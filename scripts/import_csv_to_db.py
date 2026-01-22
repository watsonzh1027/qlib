#!/usr/bin/env python3
"""
CSV to Database Import Tool

This script imports OHLCV data from CSV files to PostgreSQL database.
Duplicate records (same symbol, interval, timestamp) will be overwritten.

Usage:
    python scripts/import_csv_to_db.py
    python scripts/import_csv_to_db.py --csv-dir data/klines
    python scripts/import_csv_to_db.py --dry-run  # Preview without importing
"""

import sys
import os
from pathlib import Path
import pandas as pd
import argparse
from typing import List, Dict
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config_manager import ConfigManager
from scripts.postgres_storage import PostgreSQLStorage
from scripts.postgres_config import PostgresConfig
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def find_csv_files(csv_dir: str) -> List[Path]:
    """
    Recursively find all CSV files in the directory.
    
    Args:
        csv_dir: Root directory to search
        
    Returns:
        List of CSV file paths
    """
    csv_dir_path = Path(csv_dir)
    if not csv_dir_path.exists():
        logger.error(f"CSV directory not found: {csv_dir}")
        return []
    
    csv_files = list(csv_dir_path.rglob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files in {csv_dir}")
    return csv_files


def parse_csv_file(csv_file: Path) -> Dict:
    """
    Parse CSV file and extract metadata.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        Dict with symbol, interval, and dataframe
    """
    try:
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Validate required columns
        required_cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'interval']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"{csv_file.name}: Missing columns {missing_cols}, skipping")
            return None
        
        # Get metadata from first row
        if df.empty:
            logger.warning(f"{csv_file.name}: Empty file, skipping")
            return None
        
        symbol = df['symbol'].iloc[0]
        interval = df['interval'].iloc[0]
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        return {
            'file': csv_file,
            'symbol': symbol,
            'interval': interval,
            'dataframe': df,
            'row_count': len(df)
        }
    
    except Exception as e:
        logger.error(f"Failed to parse {csv_file.name}: {e}")
        return None


def import_to_database(data_info: Dict, postgres_storage: PostgreSQLStorage, dry_run: bool = False) -> bool:
    """
    Import data to PostgreSQL database with upsert (overwrite duplicates).
    
    Args:
        data_info: Dict with symbol, interval, and dataframe
        postgres_storage: PostgreSQL storage instance
        dry_run: If True, only preview without importing
        
    Returns:
        True if successful
    """
    symbol = data_info['symbol']
    interval = data_info['interval']
    df = data_info['dataframe']
    
    if dry_run:
        logger.info(f"[DRY RUN] Would import {len(df)} rows for {symbol} ({interval})")
        return True
    
    try:
        # Use save_ohlcv_data which handles upsert
        success = postgres_storage.save_ohlcv_data(df, symbol, interval)
        
        if success:
            logger.success(f"✅ Imported {len(df)} rows for {symbol} ({interval})")
        else:
            logger.error(f"❌ Failed to import {symbol} ({interval})")
        
        return success
    
    except Exception as e:
        logger.error(f"❌ Error importing {symbol} ({interval}): {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Import CSV data to PostgreSQL database")
    parser.add_argument(
        "--csv-dir",
        type=str,
        default="data/klines",
        help="Directory containing CSV files (default: data/klines)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files without importing"
    )
    parser.add_argument(
        "--db-env",
        action="store_true",
        help="Use environment variables for PostgreSQL config"
    )
    
    args = parser.parse_args()
    
    logger.info("🚀 CSV to Database Import Tool")
    logger.info(f"CSV Directory: {args.csv_dir}")
    logger.info(f"Dry Run: {args.dry_run}")
    
    # Find all CSV files
    csv_files = find_csv_files(args.csv_dir)
    if not csv_files:
        logger.error("No CSV files found!")
        return 1
    
    # Parse CSV files
    logger.info("📖 Parsing CSV files...")
    data_list = []
    for csv_file in tqdm(csv_files, desc="Parsing"):
        data_info = parse_csv_file(csv_file)
        if data_info:
            data_list.append(data_info)
    
    if not data_list:
        logger.error("No valid CSV files to import!")
        return 1
    
    logger.info(f"✅ Parsed {len(data_list)} valid CSV files")
    
    # Show summary
    total_rows = sum(d['row_count'] for d in data_list)
    symbols = set(d['symbol'] for d in data_list)
    intervals = set(d['interval'] for d in data_list)
    
    logger.info(f"📊 Summary:")
    logger.info(f"  - Total files: {len(data_list)}")
    logger.info(f"  - Total rows: {total_rows:,}")
    logger.info(f"  - Symbols: {len(symbols)} ({', '.join(sorted(symbols)[:5])}...)")
    logger.info(f"  - Intervals: {', '.join(sorted(intervals))}")
    
    if args.dry_run:
        logger.info("🔍 Dry run mode - no data will be imported")
        for data_info in data_list[:10]:  # Show first 10
            logger.info(f"  - {data_info['file'].name}: {data_info['symbol']} ({data_info['interval']}) - {data_info['row_count']} rows")
        if len(data_list) > 10:
            logger.info(f"  ... and {len(data_list) - 10} more files")
        return 0
    
    # Initialize PostgreSQL storage
    logger.info("🔌 Connecting to PostgreSQL...")
    
    if args.db_env:
        # Use environment variables
        postgres_config = PostgresConfig.from_env()
    else:
        # Use workflow.json
        config_manager = ConfigManager("config/workflow.json")
        db_config = config_manager.config.get("database", {})
        postgres_config = PostgresConfig(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            database=db_config.get("database", "qlib_crypto"),
            user=db_config.get("user", "crypto_user"),
            password=db_config.get("password", "change_me_in_production")
        )
    
    try:
        postgres_storage = PostgreSQLStorage(postgres_config)
        postgres_storage.connect()
        logger.success("✅ Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        return 1
    
    # Import data
    logger.info("📥 Importing data to database...")
    success_count = 0
    fail_count = 0
    
    for data_info in tqdm(data_list, desc="Importing"):
        if import_to_database(data_info, postgres_storage, dry_run=False):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 Import Summary:")
    logger.info(f"  ✅ Successful: {success_count}")
    logger.info(f"  ❌ Failed: {fail_count}")
    logger.info(f"  📈 Total rows imported: {total_rows:,}")
    logger.info("=" * 60)
    
    if fail_count > 0:
        logger.warning(f"⚠️  {fail_count} files failed to import")
        return 1
    else:
        logger.success("🎉 All files imported successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
