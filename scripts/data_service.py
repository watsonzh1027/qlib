#!/usr/bin/env python3
"""
Data Service - Automated Data Collection and Conversion Service
================================================================

This service provides automated, incremental data collection and conversion for Qlib.

Features:
- Scheduled data collection (OHLCV + Funding Rates)
- Conditional funding rate collection based on market_type
- Automatic data validation
- Incremental Qlib conversion
- Health monitoring and status reporting
- Graceful shutdown handling

Usage:
    # Start service
    python scripts/data_service.py start
    
    # Stop service
    python scripts/data_service.py stop
    
    # Check status
    python scripts/data_service.py status
    
    # Run once (manual trigger)
    python scripts/data_service.py run-once

Configuration:
    Edit config/workflow.json:
    - data.market_type: "future", "swap", or "spot"
    - data_service.enabled: true/false
    - data_service.update_interval_minutes: update frequency
    - data_service.enable_funding_rate: "auto", true, or false
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
from typing import Dict, List, Optional, Tuple
from qlib.utils.logging_config import setup_logging, startlog, endlog

# Setup logging
logger = startlog(name="data_service")

class DataServiceConfig:
    """Configuration manager for data service"""
    
    def __init__(self, config_path: str = "config/workflow.json"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            raise
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        logger.info("Configuration reloaded")
    
    @property
    def enabled(self) -> bool:
        """Check if service is enabled"""
        return self.config.get('data_service', {}).get('enabled', False)
    
    @property
    def update_interval_minutes(self) -> int:
        """Get update interval in minutes"""
        return self.config.get('data_service', {}).get('update_interval_minutes', 15)
    
    @property
    def symbols_file(self) -> str:
        """Get symbols configuration file path"""
        return self.config.get('data_service', {}).get('symbols', 'config/instruments.json')
    
    @property
    def base_interval(self) -> str:
        """Get base collection interval"""
        return self.config.get('data_service', {}).get('base_interval', '1m')
    
    @property
    def target_timeframes(self) -> List[str]:
        """Get target timeframes for conversion"""
        return self.config.get('data_service', {}).get('target_timeframes', ['15min', '60min', '240min'])
    
    @property
    def market_type(self) -> str:
        """Get market type (future, swap, or spot)"""
        return self.config.get('data', {}).get('market_type', 'future').lower()
    
    @property
    def enable_funding_rate(self) -> str:
        """Get funding rate enable setting"""
        return self.config.get('data_service', {}).get('enable_funding_rate', 'auto')
    
    @property
    def should_collect_funding_rate(self) -> bool:
        """Determine if funding rate should be collected"""
        setting = self.enable_funding_rate
        
        if setting == 'auto':
            # Auto mode: only collect for future/swap markets
            return self.market_type in ['future', 'swap']
        elif setting is True or setting == 'true':
            # Force enable
            if self.market_type == 'spot':
                logger.warning("Funding rate enabled for spot market - this may fail!")
            return True
        else:
            # Force disable
            return False
    
    @property
    def enable_validation(self) -> bool:
        """Check if data validation is enabled"""
        return self.config.get('data_service', {}).get('enable_validation', True)
    
    @property
    def enable_auto_convert(self) -> bool:
        """Check if automatic conversion is enabled"""
        return self.config.get('data_service', {}).get('enable_auto_convert', True)
    
    @property
    def max_retries(self) -> int:
        """Get maximum retry attempts"""
        return self.config.get('data_service', {}).get('max_retries', 3)
    
    @property
    def retry_delay_seconds(self) -> int:
        """Get retry delay in seconds"""
        return self.config.get('data_service', {}).get('retry_delay_seconds', 60)
    
    @property
    def pid_file(self) -> str:
        """Get PID file path"""
        return self.config.get('data_service', {}).get('pid_file', 'data/data_service.pid')
    
    @property
    def status_file(self) -> str:
        """Get status file path"""
        return self.config.get('data_service', {}).get('status_file', 'data/service_status.json')


class DataService:
    """Main data service class"""
    
    def __init__(self, config: DataServiceConfig):
        self.config = config
        self.running = False
        self.last_update_time: Optional[datetime] = None
        self.status = {
            'state': 'stopped',
            'last_update': None,
            'next_update': None,
            'total_updates': 0,
            'failed_updates': 0,
            'last_error': None
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def _is_funding_collection_time(self) -> bool:
        """
        Check if current time is within funding rate collection window.
        
        Funding rates settle every 8 hours at 00:00, 08:00, 16:00 UTC.
        Collection should happen 5-10 minutes after settlement to allow API propagation.
        
        Returns:
            True if within collection window, False otherwise
        """
        now = datetime.now(timezone.utc)
        
        # Check if we're at a settlement hour (0, 8, or 16)
        if now.hour not in [0, 8, 16]:
            return False
        
        # Check if within collection window (5-10 minutes after settlement)
        collection_start = self.config.config.get('data_service', {}).get(
            'funding_collection_window_start', 5)
        collection_end = self.config.config.get('data_service', {}).get(
            'funding_collection_window_end', 10)
        
        return collection_start <= now.minute < collection_end
    
    def _update_status(self, **kwargs):
        """Update service status"""
        self.status.update(kwargs)
        self._save_status()
    
    def _save_status(self):
        """Save status to file"""
        try:
            status_path = Path(self.config.status_file)
            status_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(status_path, 'w') as f:
                json.dump(self.status, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save status: {e}")
    
    def _load_status(self):
        """Load status from file"""
        try:
            status_path = Path(self.config.status_file)
            if status_path.exists():
                with open(status_path, 'r') as f:
                    self.status = json.load(f)
                    if self.status.get('last_update'):
                        self.last_update_time = datetime.fromisoformat(self.status['last_update'])
        except Exception as e:
            logger.error(f"Failed to load status: {e}")
    
    def _save_pid(self):
        """Save process ID to file"""
        try:
            pid_path = Path(self.config.pid_file)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(pid_path, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"PID {os.getpid()} saved to {pid_path}")
        except Exception as e:
            logger.error(f"Failed to save PID: {e}")
    
    def _remove_pid(self):
        """Remove PID file"""
        try:
            pid_path = Path(self.config.pid_file)
            if pid_path.exists():
                pid_path.unlink()
                logger.info(f"PID file {pid_path} removed")
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")
    
    def _collect_ohlcv_data(self) -> bool:
        """
        Collect OHLCV data using okx_data_collector.py
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting OHLCV data collection...")
        
        try:
            # Calculate time range (last update to now)
            end_time = datetime.now()
            
            # Try to get start_time from config (data_collection or workflow)
            dc_config = self.config.config.get("data_collection", {})
            wf_config = self.config.config.get("workflow", {})
            
            # Prioritize data_collection.start_time as it's intended for downloading
            config_start = dc_config.get("start_time") or wf_config.get("start_time")
            
            logger.info(f"Config start_time found: {config_start}")
            
            if config_start:
                try:
                    # Pass the date string directly or parse to ensure validity
                    start_time_to_pass = pd.to_datetime(config_start).strftime('%Y-%m-%dT%H:%M:%SZ')
                except Exception as e:
                    logger.warning(f"Failed to parse config start_time '{config_start}': {e}. Falling back to 365 days.")
                    start_time_to_pass = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                logger.info("No start_time found in config. Falling back to 365 days.")
                start_time_to_pass = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            
            # Get output format from config
            output_format = self.config.config.get('data_collection', {}).get('output', 'db')
            
            # Build command
            cmd = [
                'python', 'scripts/okx_data_collector.py',
                '--output', output_format,
                '--timeframes', self.config.base_interval,
                '--start_time', start_time_to_pass,
                '--end_time', end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                '--run-once'
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run collector
            result = subprocess.run(
                cmd,
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("OHLCV data collection completed successfully")
                logger.debug(f"Output: {result.stdout}")
                return True
            else:
                logger.error(f"OHLCV data collection failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("OHLCV data collection timed out")
            return False
        except Exception as e:
            logger.error(f"OHLCV data collection error: {e}")
            return False
    
    def _collect_funding_rates(self) -> bool:
        """
        Collect funding rate data (conditional based on market_type and settlement time).
        
        Funding rates settle every 8 hours (00:00, 08:00, 16:00 UTC).
        Collection only happens during the collection window (5-10 min after settlement).
        
        Returns:
            True if successful or skipped, False if failed
        """
        # Check if we should collect funding rates
        if not self.config.should_collect_funding_rate:
            logger.info(f"Skipping funding rate collection (market_type={self.config.market_type}, "
                       f"enable_funding_rate={self.config.enable_funding_rate})")
            return True
        
        # Check if we're within the funding rate collection window
        if not self._is_funding_collection_time():
            logger.debug("Not within funding rate collection window (00:05-00:10, 08:05-08:10, 16:05-16:10 UTC)")
            return True  # Not an error, just not time yet
        
        logger.info(f"Starting funding rate collection for {self.config.market_type} market...")
        
        try:
            # Import collection function
            from okx_data_collector import collect_funding_rates_for_symbols, load_symbols
            from postgres_storage import PostgreSQLStorage
            from postgres_config import PostgresConfig
            
            # Load symbols
            symbols = load_symbols(self.config.symbols_file)
            if not symbols:
                logger.warning("No symbols loaded for funding rate collection")
                return True
            
            # Initialize PostgreSQL storage
            db_config = self.config.config.get("database", {})
            postgres_config = PostgresConfig(
                host=db_config.get("host", "localhost"),
                database=db_config.get("database", "qlib_crypto"),
                user=db_config.get("user", "crypto_user"),
                password=db_config.get("password", "crypto"),
                port=db_config.get("port", 5432)
            )
            postgres_storage = PostgreSQLStorage.from_config(postgres_config)
            
            # Calculate time range (last update to now)
            end_time = datetime.now()
            if self.last_update_time:
                start_time = self.last_update_time
            else:
                # First run: collect last 30 days
                start_time = end_time - timedelta(days=30)
            
            # Collect funding rates
            success = collect_funding_rates_for_symbols(
                symbols=symbols,
                start_time=start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                end_time=end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                postgres_storage=postgres_storage
            )
            
            if success:
                logger.info("Funding rate collection completed successfully")
                return True
            else:
                logger.warning("Funding rate collection returned no results")
                return True  # Not a critical failure
        
        except Exception as e:
            logger.error(f"Funding rate collection error: {e}")
            return False
    
    def _validate_funding_rate_settlements(self, postgres_storage) -> bool:
        """
        Validate funding rate data has proper 8-hour settlement intervals.
        
        Args:
            postgres_storage: PostgreSQL storage instance
        
        Returns:
            True if validation passed, False otherwise
        """
        try:
            from okx_data_collector import load_symbols
            
            # Load symbols
            symbols = load_symbols(self.config.symbols_file)
            if not symbols:
                logger.warning("No symbols loaded for funding rate validation")
                return True
            
            # Check last 24 hours (should have 3 settlements)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            
            missing_count = 0
            total_checked = 0
            
            for symbol in symbols[:5]:  # Sample first 5 symbols
                try:
                    df = postgres_storage.get_funding_rates(
                        symbol=symbol,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if df is not None and len(df) > 0:
                        # Should have exactly 3 settlements in 24 hours
                        expected_count = 3
                        actual_count = len(df)
                        
                        if actual_count < expected_count:
                            missing_count += (expected_count - actual_count)
                            logger.warning(f"{symbol}: Only {actual_count}/3 funding settlements in last 24h")
                        
                        total_checked += 1
                    
                except Exception as e:
                    logger.debug(f"{symbol}: Could not validate funding settlements: {e}")
            
            if total_checked > 0 and missing_count > 0:
                logger.warning(f"Funding rate validation: {missing_count} missing settlements across {total_checked} symbols")
            elif total_checked > 0:
                logger.info(f"Funding rate validation passed: {total_checked} symbols have proper 8-hour settlements")
            
            return True  # Don't fail on validation warnings
            
        except Exception as e:
            logger.error(f"Funding rate settlement validation error: {e}")
            return True  # Don't fail entire validation
    
    def _validate_data(self) -> bool:
        """
        Validate collected data
        
        Returns:
            True if validation passed, False otherwise
        """
        if not self.config.enable_validation:
            logger.info("Data validation disabled, skipping")
            return True
        
        logger.info("Starting data validation...")
        
        try:
            from postgres_storage import PostgreSQLStorage
            from postgres_config import PostgresConfig
            
            # Initialize PostgreSQL storage
            db_config = self.config.config.get("database", {})
            postgres_config = PostgresConfig(
                host=db_config.get("host", "localhost"),
                database=db_config.get("database", "qlib_crypto"),
                user=db_config.get("user", "crypto_user"),
                password=db_config.get("password", "crypto"),
                port=db_config.get("port", 5432)
            )
            postgres_storage = PostgreSQLStorage.from_config(postgres_config)
            
            # Check DB health
            if postgres_storage.health_check():
                logger.info("Database health check passed")
            else:
                logger.error("Database health check failed")
                return False
            
            # Validate funding rate settlements if enabled
            if self.config.should_collect_funding_rate:
                self._validate_funding_rate_settlements(postgres_storage)
            
            return True
        
        except Exception as e:
            logger.error(f"Data validation error: {e}")
            return False
    
    def _convert_to_qlib(self) -> bool:
        """
        Convert data to Qlib format
        
        Returns:
            True if successful, False otherwise
        """
        if not self.config.enable_auto_convert:
            logger.info("Auto-conversion disabled, skipping")
            return True
        
        logger.info("Starting Qlib conversion...")
        
        try:
            # Get data source from config
            data_source = self.config.config.get('data_convertor', {}).get('data_source', 'db')
            
            # Build command
            cmd = [
                'python', 'scripts/convert_to_qlib.py',
                '--source', data_source
            ]
            
            # Add timeframes
            for tf in self.config.target_timeframes:
                cmd.extend(['--timeframes', tf])
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run conversion
            result = subprocess.run(
                cmd,
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("Qlib conversion completed successfully")
                
                # Verify Qlib data health
                logger.info("Verifying Qlib data health...")
                for tf in self.config.target_timeframes:
                    qlib_dir = f"data/qlib_data/crypto_{tf}"
                    if os.path.exists(qlib_dir):
                        logger.info(f"Checking health for {tf} at {qlib_dir}")
                        check_cmd = [
                            'python', 'scripts/check_data_health.py',
                            '--qlib_dir', qlib_dir,
                            '--freq', tf
                        ]
                        subprocess.run(check_cmd, cwd=os.getcwd(), capture_output=True)
                
                return True
            else:
                logger.error(f"Qlib conversion failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Qlib conversion timed out")
            return False
        except Exception as e:
            logger.error(f"Qlib conversion error: {e}")
            return False
    
    def _run_update_cycle(self) -> bool:
        """
        Run a complete update cycle
        
        Returns:
            True if all steps succeeded, False otherwise
        """
        logger.info("=" * 80)
        logger.info("Starting update cycle")
        logger.info("=" * 80)
        
        cycle_start = datetime.now()
        
        # Step 1: Collect OHLCV data
        if not self._collect_ohlcv_data():
            logger.error("Update cycle failed at OHLCV collection")
            return False
        
        # Step 2: Collect funding rates (conditional)
        if not self._collect_funding_rates():
            logger.error("Update cycle failed at funding rate collection")
            return False
        
        # Step 3: Validate data
        if not self._validate_data():
            logger.error("Update cycle failed at data validation")
            return False
        
        # Step 4: Convert to Qlib format
        if not self._convert_to_qlib():
            logger.error("Update cycle failed at Qlib conversion")
            return False
        
        cycle_end = datetime.now()
        duration = (cycle_end - cycle_start).total_seconds()
        
        logger.info("=" * 80)
        logger.info(f"Update cycle completed successfully in {duration:.1f} seconds")
        logger.info("=" * 80)
        
        # Update status
        self.last_update_time = cycle_end
        self._update_status(
            last_update=cycle_end.isoformat(),
            total_updates=self.status['total_updates'] + 1,
            last_error=None
        )
        
        return True
    
    def run_once(self) -> bool:
        """
        Run a single update cycle
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Running single update cycle...")
        
        # Load previous status
        self._load_status()
        
        # Run update
        success = self._run_update_cycle()
        
        if not success:
            self._update_status(
                failed_updates=self.status['failed_updates'] + 1,
                last_error=f"Update failed at {datetime.now().isoformat()}"
            )
        
        return success
    
    def start(self):
        """Start the data service"""
        if not self.config.enabled:
            logger.error("Data service is disabled in configuration")
            return
        
        logger.info("Starting data service...")
        logger.info(f"Update interval: {self.config.update_interval_minutes} minutes")
        logger.info(f"Market type: {self.config.market_type}")
        logger.info(f"Funding rate collection: {self.config.should_collect_funding_rate}")
        
        # Save PID
        self._save_pid()
        
        # Load previous status
        self._load_status()
        
        # Update status
        self._update_status(state='running')
        
        self.running = True
        
        try:
            while self.running:
                # Calculate next update time
                if self.last_update_time:
                    next_update = self.last_update_time + timedelta(minutes=self.config.update_interval_minutes)
                else:
                    next_update = datetime.now()
                
                self._update_status(next_update=next_update.isoformat())
                
                # Wait until next update time
                now = datetime.now()
                if now < next_update:
                    wait_seconds = (next_update - now).total_seconds()
                    logger.info(f"Next update at {next_update.strftime('%Y-%m-%d %H:%M:%S')} "
                               f"(in {wait_seconds/60:.1f} minutes)")
                    
                    # Sleep in small intervals to allow for graceful shutdown
                    while self.running and datetime.now() < next_update:
                        time.sleep(1)
                    
                    if not self.running:
                        break
                
                # Run update cycle with retries
                retry_count = 0
                success = False
                
                while retry_count < self.config.max_retries and not success:
                    if retry_count > 0:
                        logger.info(f"Retry attempt {retry_count}/{self.config.max_retries}")
                        time.sleep(self.config.retry_delay_seconds)
                    
                    success = self._run_update_cycle()
                    
                    if not success:
                        retry_count += 1
                
                if not success:
                    logger.error(f"Update cycle failed after {self.config.max_retries} retries")
                    self._update_status(
                        failed_updates=self.status['failed_updates'] + 1,
                        last_error=f"Update failed after {self.config.max_retries} retries at {datetime.now().isoformat()}"
                    )
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the data service"""
        logger.info("Stopping data service...")
        self.running = False
        self._update_status(state='stopped')
        self._remove_pid()
        logger.info("Data service stopped")


def get_service_pid(config: DataServiceConfig) -> Optional[int]:
    """Get PID of running service"""
    try:
        pid_path = Path(config.pid_file)
        if pid_path.exists():
            with open(pid_path, 'r') as f:
                return int(f.read().strip())
    except Exception as e:
        logger.error(f"Failed to read PID file: {e}")
    return None


def is_service_running(config: DataServiceConfig) -> bool:
    """Check if service is running"""
    pid = get_service_pid(config)
    if pid is None:
        return False
    
    try:
        # Check if process exists
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def show_status(config: DataServiceConfig):
    """Show service status"""
    print("\n" + "=" * 80)
    print("Data Service Status")
    print("=" * 80)
    
    # Check if running
    running = is_service_running(config)
    pid = get_service_pid(config)
    
    print(f"Service State: {'RUNNING' if running else 'STOPPED'}")
    if pid:
        print(f"Process ID: {pid}")
    
    # Load status file
    try:
        status_path = Path(config.status_file)
        if status_path.exists():
            with open(status_path, 'r') as f:
                status = json.load(f)
            
            print(f"\nConfiguration:")
            print(f"  Market Type: {config.market_type}")
            print(f"  Update Interval: {config.update_interval_minutes} minutes")
            print(f"  Funding Rate Collection: {config.should_collect_funding_rate}")
            print(f"  Auto Validation: {config.enable_validation}")
            print(f"  Auto Conversion: {config.enable_auto_convert}")
            
            print(f"\nStatistics:")
            print(f"  Total Updates: {status.get('total_updates', 0)}")
            print(f"  Failed Updates: {status.get('failed_updates', 0)}")
            
            if status.get('last_update'):
                print(f"  Last Update: {status['last_update']}")
            
            if status.get('next_update'):
                print(f"  Next Update: {status['next_update']}")
            
            if status.get('last_error'):
                print(f"\n  Last Error: {status['last_error']}")
        else:
            print("\nNo status file found")
    
    except Exception as e:
        print(f"\nError reading status: {e}")
    
    print("=" * 80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Qlib Data Service - Automated data collection and conversion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'command',
        choices=['start', 'stop', 'status', 'run-once'],
        help='Service command'
    )
    
    parser.add_argument(
        '--config',
        default='config/workflow.json',
        help='Configuration file path (default: config/workflow.json)'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = DataServiceConfig(args.config)
    
    # Execute command
    if args.command == 'start':
        if is_service_running(config):
            print(f"Service is already running (PID: {get_service_pid(config)})")
            sys.exit(1)
        
        service = DataService(config)
        service.start()
    
    elif args.command == 'stop':
        pid = get_service_pid(config)
        if pid is None:
            print("Service is not running")
            sys.exit(1)
        
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to process {pid}")
            
            # Wait for process to stop
            for _ in range(30):
                time.sleep(1)
                if not is_service_running(config):
                    print("Service stopped successfully")
                    break
            else:
                print("Service did not stop gracefully, sending SIGKILL")
                os.kill(pid, signal.SIGKILL)
        
        except Exception as e:
            print(f"Error stopping service: {e}")
            sys.exit(1)
    
    elif args.command == 'status':
        show_status(config)
    
    elif args.command == 'run-once':
        service = DataService(config)
        success = service.run_once()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
