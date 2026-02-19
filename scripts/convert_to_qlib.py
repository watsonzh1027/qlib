import os
import sys
import pandas as pd
import tempfile
import numpy as np
import time
import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from loguru import logger
from qlib.utils import fname_to_code, code_to_fname
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import argparse
from datetime import datetime, timezone

# Add project root to Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config_manager import ConfigManager
from scripts.dump_bin import DumpDataAll  # Import DumpDataAll for binary conversion
from scripts.symbol_utils import normalize_symbol  # Import symbol normalization

from qlib.utils.logging_config import setup_logging, startlog, endlog

# Setup logging
logger = startlog(name="data_service")

def calculate_proportion_segments(start_date, end_date, proportions):
    """
    Calculate date segments from proportions.
    
    Args:
        start_date: Start date (string or datetime)
        end_date: End date (string or datetime) 
        proportions: Dict of segment names to proportion integers
        
    Returns:
        Dict of segment names to (start_date, end_date) tuples
    """
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    total = sum(proportions.values())
    
    current = start_ts
    result = {}
    
    for seg, prop in proportions.items():
        if prop <= 0:
            raise ValueError(f"Proportion for segment '{seg}' must be positive")
        
        duration = (end_ts - start_ts) * prop / total
        end_seg = current + duration
        result[seg] = (str(current.date()), str(end_seg.date()))
        current = end_seg
    
    return result

def weighted_average(x, weights):
    """Calculate weighted average."""
    try:
        return np.average(x, weights=weights.loc[x.index])
    except Exception:
        return np.nan


class PostgreSQLStorage:
    """PostgreSQL database storage class for retrieving kline data."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str,
                 table: str = "kline_data", schema: Optional[Dict[str, str]] = None):
        """
        Initialize PostgreSQL connection.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            table: Table name containing kline data
            schema: Column mapping dictionary (optional)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.table = table
        self.schema = schema or {
            'timestamp': 'timestamp',
            'symbol': 'symbol',
            'interval': 'interval',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }
        self.connection = None

    def connect(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Establish database connection with retry logic.

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    connect_timeout=10  # 10 second timeout
                )
                logger.info("Successfully connected to PostgreSQL database")
                return
            except psycopg2.OperationalError as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
            except psycopg2.Error as e:
                last_error = e
                logger.error(f"Database connection error: {e}")
                break

        raise ConnectionError(f"Could not establish database connection: {last_error}")

    def get_funding_rates(self, symbol: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         start_time: Optional[str] = None,
                         end_time: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve funding rate data for a specific symbol.

        Accepts either `start_date`/`end_date` or `start_time`/`end_time` for compatibility with various callers.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT', 'ETHUSDT')
            start_date/start_time: Start date/time in ISO format (optional)
            end_date/end_time: End date/time in ISO format (optional)

        Returns:
            DataFrame with funding rate data
        """
        # Normalize aliases
        if start_date is None and start_time is not None:
            start_date = start_time
        if end_date is None and end_time is not None:
            end_date = end_time

        if not self.connection:
            raise ConnectionError("Database connection not established")

        query = sql.SQL(
            "SELECT timestamp, funding_rate FROM funding_rates WHERE symbol = %s"
        )
        params = [symbol]

        if start_date:
            query = sql.SQL("{} AND timestamp >= %s").format(query)
            params.append(start_date)

        if end_date:
            query = sql.SQL("{} AND timestamp <= %s").format(query)
            params.append(end_date)

        query = sql.SQL("{} ORDER BY timestamp").format(query)

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                if not rows:
                    logger.info(f"No funding rate data found for {symbol}")
                    return pd.DataFrame()

                df = pd.DataFrame(rows)
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                logger.info(f"Retrieved {len(df)} funding rate records for {symbol}")
                return df

        except psycopg2.Error as e:
            logger.warning(f"Error fetching funding rates for {symbol}: {e}")
            return pd.DataFrame()

    def get_kline_data(self, symbol: str, interval: str,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Retrieve kline data for a specific symbol and interval.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            interval: Time interval (e.g., '1m', '15m', '1h')
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)

        Returns:
            DataFrame with kline data
        """
        if not self.connection:
            raise ConnectionError("Database connection not established")

        # Build query with proper column mapping
        columns = [
            sql.Identifier(self.schema['timestamp']),
            sql.Identifier(self.schema['symbol']),
            sql.Identifier(self.schema['interval']),
            sql.Identifier(self.schema['open']),
            sql.Identifier(self.schema['high']),
            sql.Identifier(self.schema['low']),
            sql.Identifier(self.schema['close']),
            sql.Identifier(self.schema['volume'])
        ]

        query = sql.SQL("SELECT {} FROM {} WHERE {} = %s AND {} = %s").format(
            sql.SQL(', ').join(columns),
            sql.Identifier(self.table),
            sql.Identifier(self.schema['symbol']),
            sql.Identifier(self.schema['interval'])
        )

        params = [symbol, interval]

        # Add date filters if provided
        if start_date:
            query = sql.SQL("{} AND {} >= %s").format(query, sql.Identifier(self.schema['timestamp']))
            params.append(start_date)

        if end_date:
            query = sql.SQL("{} AND {} <= %s").format(query, sql.Identifier(self.schema['timestamp']))
            params.append(end_date)

        # Order by timestamp
        query = sql.SQL("{} ORDER BY {}").format(query, sql.Identifier(self.schema['timestamp']))

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                if not rows:
                    logger.warning(f"No data found for symbol {symbol}, interval {interval}")
                    return pd.DataFrame()

                # Convert to DataFrame
                df = pd.DataFrame(rows)

                # Rename columns to standard format
                column_mapping = {v: k for k, v in self.schema.items()}
                df = df.rename(columns=column_mapping)

                # Ensure timestamp is datetime, handling timezone-aware timestamps
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

                logger.info(f"Retrieved {len(df)} records for {symbol} {interval}")
                return df

        except psycopg2.Error as e:
            logger.error(f"Database query error: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error

    def get_available_symbols(self, interval: Optional[str] = None) -> List[str]:
        """
        Get list of available symbols in the database.

        Args:
            interval: Filter by specific interval (optional)

        Returns:
            List of symbol strings
        """
        if not self.connection:
            raise ConnectionError("Database connection not established")

        query = sql.SQL("SELECT DISTINCT {} FROM {}").format(
            sql.Identifier(self.schema['symbol']),
            sql.Identifier(self.table)
        )

        params = []
        if interval:
            query = sql.SQL("{} WHERE {} = %s").format(query, sql.Identifier(self.schema['interval']))
            params.append(interval)

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                symbols = [row[0] for row in rows]
                logger.info(f"Found {len(symbols)} available symbols")
                return symbols

        except psycopg2.Error as e:
            logger.error(f"Database query error: {e}")
            return []  # Return empty list if table doesn't exist or other error

    def validate_schema(self) -> bool:
        """
        Validate that the database table has the expected schema.

        Returns:
            True if schema is valid, False otherwise
        """
        if not self.connection:
            raise ConnectionError("Database connection not established")

        required_columns = set(self.schema.values())

        try:
            # Get table columns
            query = sql.SQL("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """)

            with self.connection.cursor() as cursor:
                cursor.execute(query, [self.table])
                existing_columns = {row[0] for row in cursor.fetchall()}

                missing_columns = required_columns - existing_columns
                if missing_columns:
                    logger.error(f"Missing required columns in table {self.table}: {missing_columns}")
                    return False

                logger.info(f"Database schema validation passed for table {self.table}")
                return True

        except psycopg2.Error as e:
            logger.error(f"Schema validation error: {e}")
            return False

    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate data quality and return statistics.

        Args:
            df: DataFrame to validate

        Returns:
            Dictionary with validation results and statistics
        """
        if df.empty:
            return {
                'valid': False,
                'error': 'DataFrame is empty',
                'statistics': {}
            }

        stats = {
            'total_records': len(df),
            'date_range': {
                'start': df['timestamp'].min().isoformat() if not df.empty else None,
                'end': df['timestamp'].max().isoformat() if not df.empty else None
            },
            'symbols': df['symbol'].unique().tolist() if 'symbol' in df.columns else [],
            'intervals': df['interval'].unique().tolist() if 'interval' in df.columns else [],
            'missing_values': df.isnull().sum().to_dict(),
            'duplicate_timestamps': df['timestamp'].duplicated().sum()
        }

        # Check for data quality issues
        issues = []

        # Check for missing OHLCV values
        ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in ohlcv_cols:
            if col in df.columns and df[col].isnull().any():
                issues.append(f"Missing values in {col} column")

        # Check for negative prices/volumes
        if 'open' in df.columns and (df['open'] <= 0).any():
            issues.append("Negative or zero open prices found")
        if 'volume' in df.columns and (df['volume'] < 0).any():
            issues.append("Negative volume values found")

        # Check for OHLC logic (high >= low, etc.)
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            invalid_ohlc = (
                (df['high'] < df['low']) |
                (df['open'] < df['low']) |
                (df['open'] > df['high']) |
                (df['close'] < df['low']) |
                (df['close'] > df['high'])
            ).sum()
            if invalid_ohlc > 0:
                issues.append(f"{invalid_ohlc} records have invalid OHLC relationships")

        stats['issues'] = issues
        stats['valid'] = len(issues) == 0

        return stats

    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class DumpDataCrypto(DumpDataAll):
    """Custom dumper for crypto data that skips calendar creation since crypto markets are 24/7."""
    
    def __init__(self, mode="all", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.all_data = {}  # Will be set externally
        self._old_calendar_list = []
    
    def get_symbol_from_file(self, file_path: Path) -> str:
        """Convert file path to symbol, handling hierarchical naming."""
        # We use '#' as a separator in temp files to represent '/' in qlib symbols
        return file_path.stem.replace('#', '/')
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol while preserving hierarchical structure casing."""
        return symbol
    
    def _dump_features(self):
        logger.info("start dump features......")
        # For crypto data, dump without calendar alignment
        _dump_func = partial(self._dump_bin_crypto, calendar_list=[])
        with tqdm(total=len(self.df_files)) as p_bar:
            with ProcessPoolExecutor(max_workers=self.works) as executor:
                for _ in executor.map(_dump_func, self.df_files):
                    p_bar.update()

        logger.info("end of features dump.\n")
    
    def _dump_bin_crypto(self, file_or_data, calendar_list):
        """Dump binary data for crypto without requiring calendar alignment."""
        if isinstance(file_or_data, pd.DataFrame):
            if file_or_data.empty:
                return
            raw_symbol = str(file_or_data.iloc[0][self.symbol_field_name])
            code = raw_symbol  # Keep casing as provided
            df = file_or_data
        elif isinstance(file_or_data, Path):
            code = self.get_symbol_from_file(file_or_data)
            df = self._get_source_data(file_or_data)
        else:
            raise ValueError(f"not support {type(file_or_data)}")
        if df is None or df.empty:
            logger.warning(f"{code} data is None or empty")
            return

        # try to remove dup rows or it will cause exception when reindex.
        df = df.drop_duplicates(self.date_field_name)

        # features save dir - match Qlib's lowercase expectation on disk
        # code is like "ETH_USDT/240min/FUTURE"
        features_dir = self._features_dir.joinpath(code.lower())
        features_dir.mkdir(parents=True, exist_ok=True)
        
        # For crypto, save data directly without calendar alignment
        self._data_to_bin_crypto(df, features_dir)
    
    def _data_to_bin_crypto(self, df: pd.DataFrame, features_dir: Path):
        """Save data to binary format for crypto without calendar alignment."""
        if df.empty:
            logger.warning(f"{features_dir.name} data is None or empty")
            return
        
        # For crypto, align data with calendar timestamps
        _df = df.copy()
        
        # Ensure timestamp is datetime and set as index
        _df[self.date_field_name] = pd.to_datetime(_df[self.date_field_name])
        _df = _df.set_index(self.date_field_name)
        
        # Check for excessive NaN values
        nan_ratio = _df.isnull().mean().mean()
        
        if nan_ratio > 0.5:  # If more than 50% NaN, skip this symbol
            logger.warning(f"{features_dir.name}: Too many NaN values ({nan_ratio:.3f}), skipping")
            return
        
        # Fill NaN values
        _df = _df.ffill().bfill().interpolate(method='linear').fillna(0)
        
        # Calculate start index
        # For ALL mode: start_index is relative to the FULL calendar
        # For UPDATE mode: we are appending, so we just write the values.
        # But wait, Qlib bin file structure is [start_index, value1, value2...]
        # If we append, we are just adding valueX, valueY... to the end of the file.
        # The start_index at the beginning of the file remains valid for the *entire* sequence.
        # However, we must ensure that the new data strictly follows the existing data in the calendar.
        
        # We assume _df contains ONLY new data in UPDATE mode.
        
        # Determine mode logic
        # If file exists and mode is update -> Append
        # Else -> Write new
        
        # Use simple heuristic: if bin file exists and size > 0, append.
        
        dump_fields = self.get_dump_fields(_df.columns)
        dump_fields = [f for f in dump_fields if f != self.date_field_name]
        
        for field in dump_fields:
            if field not in _df.columns:
                continue
                
            field_data = _df[field].values.astype(np.float32)
            bin_path = features_dir.joinpath(f"{field.lower()}.{self.freq.lower()}.bin")
            
            if self.mode == "update" and bin_path.exists():
                # Append mode
                with bin_path.open("ab") as fp:
                    field_data.tofile(fp)
                logger.debug(f"Appended {field} to {bin_path}, size: {len(field_data)}")
            else:
                # Write mode (ALL or new file)
                # Need to calculate start_index relative to the GLOBAL calendar
                # In DumpDataAll, this is done via self.get_datetime_index(_df, calendar_list)
                # But here we are processing per-symbol.
                # If it's a new file in ALL mode, start_index is the index of the first timestamp 
                # in the full calendar.
                
                # To get the full calendar, we use self._calendars_list which is set in dump()
                if not self._calendars_list:
                     logger.warning("Calendar list empty, cannot calculate start index.")
                     start_index = 0
                else:
                     try:
                         # Ensure checking against timezone-naive or aware consistently
                         # self._calendars_list are Timestamps. _df.index are Timestamps.
                         # normalize to naive UTC
                         first_time = _df.index.min()
                         if first_time.tzinfo:
                             first_time = first_time.tz_localize(None)
                         
                         # Find index
                         # self._calendars_list is sorted.
                         import bisect
                         # bisect_left returns insertion point. 
                         # We want exact match usually, or nearest?
                         # Qlib expects aligned data.
                         start_index = bisect.bisect_left(self._calendars_list, first_time)
                         
                         # check if match
                         if start_index < len(self._calendars_list) and self._calendars_list[start_index] != first_time:
                             # warn?
                             pass
                     except Exception as e:
                         logger.warning(f"Error calculating start index: {e}, default to 0")
                         start_index = 0

                data_array = np.concatenate([[start_index], field_data]).astype(np.float32)
                data_array.astype("<f").tofile(str(bin_path))
                logger.debug(f"Saved {field} to {bin_path}, start_index: {start_index}, size: {len(data_array)}")
    
    def dump(self):
        # 1. Prepare Calendar
        if self.mode == "update":
            # Load existing calendar
            qlib_freq = convert_interval_to_qlib_freq(self.freq)
            calendar_path = self._calendars_dir.joinpath(f"{qlib_freq}.txt")
            if calendar_path.exists():
                with open(calendar_path, "r") as f:
                    self._old_calendar_list = [pd.Timestamp(line.strip()) for line in f.readlines()]
            else:
                logger.warning("Update mode but no existing calendar found. Switching behavior to 'all'.")
        
        # 2. Merge/Create Calendar
        self._dump_calendars_crypto()
        
        # 3. Features
        self._dump_features()
        
        # 4. Instruments
        self._dump_instruments_crypto()
    
    def _dump_instruments_crypto(self):
        """Create instruments file for crypto data using all_data."""
        logger.info("start dump instruments for crypto......")
        
        # In update mode, we need to merge with existing instruments
        existing_instruments = {}
        if self.mode == "update":
            inst_path = self._instruments_dir.joinpath(self.INSTRUMENTS_FILE_NAME)
            if inst_path.exists():
                try:
                    df_inst = pd.read_csv(inst_path, sep='\t', header=None, names=['symbol', 'start', 'end'])
                    existing_instruments = df_inst.set_index('symbol').to_dict(orient='index')
                except Exception as e:
                    logger.warning(f"Failed to load existing instruments: {e}")

        date_range_list = []
        
        # Process current batch
        for symbol, df in self.all_data.items():
            if not df.empty and self.date_field_name in df.columns:
                timestamps = pd.to_datetime(df[self.date_field_name])
                start_time = timestamps.min()
                end_time = timestamps.max()
                
                # Check against existing
                if symbol in existing_instruments:
                    old_start = pd.to_datetime(existing_instruments[symbol]['start'])
                    old_end = pd.to_datetime(existing_instruments[symbol]['end'])

                    # Ensure timezone consistency
                    if start_time.tzinfo is not None and old_start.tzinfo is None:
                         old_start = old_start.tz_localize('UTC')
                    if end_time.tzinfo is not None and old_end.tzinfo is None:
                         old_end = old_end.tz_localize('UTC')
                         
                    # Or conversely if start_time is naive (unlikely given DB source but possible from CSV)
                    if start_time.tzinfo is None and old_start.tzinfo is not None:
                         start_time = start_time.tz_localize('UTC')
                    if end_time.tzinfo is None and old_end.tzinfo is not None:
                         end_time = end_time.tz_localize('UTC')
                    
                    # Update range
                    start_time = min(start_time, old_start)
                    end_time = max(end_time, old_end)
                    
                    # Remove from existing so we don't duplicate
                    del existing_instruments[symbol]
                
                begin_time_str = self._format_datetime(start_time)
                end_time_str = self._format_datetime(end_time)
                
                inst_fields = [symbol, begin_time_str, end_time_str]
                date_range_list.append(f"{self.INSTRUMENTS_SEP.join(inst_fields)}")
        
        # Add remaining existing instruments that weren't in the update batch
        for symbol, dates in existing_instruments.items():
            inst_fields = [symbol, dates['start'], dates['end']]
            date_range_list.append(f"{self.INSTRUMENTS_SEP.join(inst_fields)}")
        
        # Sort by symbol
        date_range_list.sort()
        
        self.save_instruments(date_range_list)
        logger.info("end of instruments dump.\n")
    
    def _dump_calendars_crypto(self):
        """Create calendar file for crypto data using data from memory."""
        logger.info("start dump calendars for crypto......")
        
        # use dates from memory
        new_dates = []
        for qlib_symbol, df in self.all_data.items():
            new_dates.extend(df[self.date_field_name].tolist())
        
        if not new_dates and not self._old_calendar_list:
            logger.warning("No data found to generate calendar")
            return
            
        # Combine
        combined_dates = self._old_calendar_list + new_dates
        
        # Dedup and Sort
        start = time.time()
        # Ensure all naive UTC 
        dt_index = pd.to_datetime(combined_dates, utc=True).tz_localize(None)
        self._calendars_list = sorted(list(set(dt_index)))
        logger.info(f"Calendar dedup/sort processed in {time.time()-start:.2f}s")
        
        # Save to target freq
        qlib_freq = convert_interval_to_qlib_freq(self.freq)
        self._calendars_dir.mkdir(parents=True, exist_ok=True)
        calendar_path = self._calendars_dir.joinpath(f"{qlib_freq}.txt")
        with open(calendar_path, "w") as f:
            for d in self._calendars_list:
                f.write(f"{d}\n")
                
        logger.info(f"Updated calendar {qlib_freq} with {len(self._calendars_list)} timestamps")
        logger.info("end of calendars dump.\n")

"""
Convert OHLCV data from CSV format to Qlib-compatible binary format.

This module processes crypto OHLCV data organized by symbol directories,
merges CSV files, validates integrity, and converts to Qlib binary format
(instruments and features only, no calendars for continuous trading data).
Frequency is dynamically set from the 'interval' column (e.g., "15m").
"""

# Load configuration
config_manager = ConfigManager("config/workflow.json")
config = config_manager.config

# Debug: print data_source
print(f"DEBUG: data_source from config: {config.get('data_convertor', {}).get('data_source', 'NOT_FOUND')}")

# Update input_dir and output_dir to use centralized parameters
input_dir = config.get("data", {}).get("csv_data_dir", "data/klines")
output_dir = os.path.abspath(config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto"))

def validate_data_integrity(df, freq, date_field="date"):
    """
    Validate data integrity by checking for gaps and ensuring correct timestamps.

    Args:
        df (pd.DataFrame): DataFrame containing OHLCV data.
        freq (str): Frequency string for pd.date_range (e.g., "15T" for 15 minutes).
        date_field (str): Name of the date/time column.
    
    Returns:
        bool: True if data is valid, False otherwise.
    """
    if df.empty:
        return False
    # Convert date_field to datetime
    df_copy = df.copy()
    df_copy[date_field] = pd.to_datetime(df_copy[date_field])
    # Check for missing timestamps
    expected_intervals = pd.date_range(
        start=df_copy[date_field].min(),
        end=df_copy[date_field].max(),
        freq=freq
    )
    actual_intervals = df_copy[date_field]
    return set(expected_intervals).issubset(set(actual_intervals))


def convert_interval_to_qlib_freq(interval: str) -> str:
    """
    Convert interval string to qlib frequency format.
    
    Args:
        interval: Interval string like "1h", "15m", "1m"
        
    Returns:
        Qlib frequency string like "60min", "15min", "1min"
    """
    if interval == "1h":
        return "60min"
    elif interval == "15m":
        return "15min"
    elif interval == "1m":
        return "1min"
    else:
        # Assume already in qlib format or handle other cases
        return interval.replace("h", "60min").replace("m", "min") if interval.endswith(("h", "m")) else interval


_SUMMARY_LOGGED = False


def _load_instrument_symbols(config: Dict[str, Any]) -> List[str]:
    data_config = config.get("data", {})
    data_convertor = config.get("data_convertor", {})
    instruments_file = data_convertor.get("instruments_file") or data_config.get("symbols")
    if instruments_file == "<data.symbols>":
        instruments_file = data_config.get("symbols")
    if not instruments_file:
        return []

    if not os.path.isabs(instruments_file):
        instruments_file = os.path.join(str(project_root), instruments_file)

    try:
        with open(instruments_file, "r") as f:
            inst_data = json.load(f)
        return inst_data.get("symbols", [])
    except Exception as e:
        logger.warning(f"Failed to load instruments file {instruments_file}: {e}")
        return []


def funding_rate_summary_from_csv(
    symbols: List[str],
    base_dir: str,
    interval: str,
) -> Dict[str, Optional[str]]:
    summary: Dict[str, Optional[str]] = {}

    for symbol in symbols:
        symbol_safe = symbol.replace("/", "_")
        candidates = [
            os.path.join(base_dir, symbol_safe, f"{symbol_safe}_{interval}.csv"),
            os.path.join(base_dir, symbol_safe, f"{symbol_safe}.csv"),
        ]
        csv_path = next((fp for fp in candidates if os.path.exists(fp)), None)
        if csv_path is None:
            summary[symbol] = None
            continue

        try:
            header = pd.read_csv(csv_path, nrows=0)
            if "funding_rate" not in header.columns or "timestamp" not in header.columns:
                summary[symbol] = None
                continue

            start_ts = None
            for chunk in pd.read_csv(csv_path, usecols=["timestamp", "funding_rate"], chunksize=100000):
                chunk = chunk.dropna(subset=["funding_rate", "timestamp"])
                if chunk.empty:
                    continue

                mask = chunk["funding_rate"].astype(float) != 0.0
                if not mask.any():
                    continue

                ts = pd.to_datetime(chunk.loc[mask, "timestamp"], utc=True, errors="coerce").dropna()
                if not ts.empty:
                    start_ts = ts.min().isoformat()
                    break

            summary[symbol] = start_ts
        except Exception as e:
            logger.warning(f"Failed to read funding_rate from {csv_path}: {e}")
            summary[symbol] = None

    return summary


def _funding_rate_summary_from_db(
    symbols: List[str],
    db_config: Dict[str, Any],
) -> Dict[str, Optional[str]]:
    summary: Dict[str, Optional[str]] = {}
    conn = None

    try:
        conn = psycopg2.connect(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            database=db_config.get("database", "qlib_crypto"),
            user=db_config.get("user", "crypto_user"),
            password=db_config.get("password", "change_me_in_production"),
            connect_timeout=10,
        )
        query = (
            "SELECT MIN(timestamp) "
            "FROM funding_rates "
            "WHERE symbol = %s "
            "AND funding_rate IS NOT NULL "
            "AND funding_rate <> 0"
        )
        with conn.cursor() as cursor:
            for symbol in symbols:
                cursor.execute(query, (symbol,))
                row = cursor.fetchone()
                start_ts = row[0] if row and row[0] else None
                if start_ts is not None:
                    start_ts = pd.Timestamp(start_ts, tz="UTC").isoformat()
                summary[symbol] = start_ts
    except Exception as e:
        logger.warning(f"Failed to query funding_rate summary from DB: {e}")
        return {}
    finally:
        if conn is not None:
            conn.close()

    return summary


def _log_conversion_summary(config: Dict[str, Any], source: str) -> None:
    global _SUMMARY_LOGGED
    if _SUMMARY_LOGGED:
        return

    symbols = _load_instrument_symbols(config)
    if not symbols:
        logger.warning("Conversion summary skipped: no symbols loaded")
        _SUMMARY_LOGGED = True
        return

    data_config = config.get("data", {})
    data_collection = config.get("data_collection", {})
    db_config = config.get("database", {})
    base_dir = data_config.get("csv_data_dir", "data/klines")
    interval = data_collection.get("interval", "1m")

    if source in ["db", "both"]:
        summary = _funding_rate_summary_from_db(symbols, db_config)
    else:
        summary = funding_rate_summary_from_csv(symbols, base_dir, interval)

    if not summary:
        logger.warning("Conversion summary skipped: no funding_rate data available")
        _SUMMARY_LOGGED = True
        return

    logger.info("Conversion summary: funding_rate start times per symbol")
    for symbol in sorted(summary.keys()):
        start_time = summary[symbol]
        if start_time is None:
            logger.info(f"Funding rate start - {symbol}: None")
        else:
            logger.info(f"Funding rate start - {symbol}: {start_time}")

    _SUMMARY_LOGGED = True


def convert_to_qlib(source: str = None, freq: str = None, force: bool = False):
    """
    Convert cryptocurrency data to Qlib format.
    
    Args:
        source: Data source ('csv', 'db', or 'both'). If None, reads from config.
        freq: Target frequency (e.g., '15min', '60min'). If None, reads from config.
        force: If True, forces full re-conversion ignoring existing data.
    """
    # Get configuration parameters
    data_config = config.get("data", {})
    data_convertor = config.get("data_convertor", {})
    data_collection = config.get("data_collection", {})
    db_config = config.get("database", {})
    
    # Determine data source
    if source is None:
        source = data_convertor.get("data_source", "csv")
        
    if source not in ["csv", "db", "both"]:
        raise ValueError(f"Invalid data source: {source}")
    
    input_dir = data_config.get("csv_data_dir", "data/klines")
    # Base output dir (allow data_convertor.provider_uri override)
    provider_uri = data_convertor.get("provider_uri")
    if provider_uri == "<data.bin_data_dir>":
        provider_uri = data_config.get("bin_data_dir")
    base_output_dir = os.path.abspath(provider_uri or data_config.get("bin_data_dir", "data/qlib_data/crypto"))
    
    # Get convertor parameters
    date_field_name = data_convertor.get("date_field_name", "timestamp")
    include_fields = data_convertor.get("include_fields", ["open", "high", "low", "close", "volume"])
    symbol_field_name = "symbol"  # Assuming default, can be added to config if needed
    
    # Get interval from config and convert to qlib frequency
    if source == 'db':
        # If using DB source, try to infer source interval from target frequency
        target_freq = freq if freq else config.get("workflow", {}).get("frequency", "60min")
        interval_map_rev = {"1min": "1m", "5min": "5m", "15min": "15m", "30min": "30m", "60min": "1h", "240min": "4h", "1day": "1d"}
        
        # We need to map TARGET freq (e.g. 60min) to DB interval (e.g. 1h)
        # Check if target_freq is in keys
        if target_freq in interval_map_rev:
             interval = interval_map_rev[target_freq]
        else:
             # Fallback logic or error
             logger.warning(f"Unknown target freq {target_freq}, defaulting to 1h retrieval")
             interval = data_collection.get("interval", "1h")

        logger.info(f"Inferred DB retrieval interval '{interval}' from target frequency '{target_freq}'")
    else:
        interval = data_collection.get("interval", "1h")
        target_freq = freq if freq else config.get("workflow", {}).get("frequency", "60min")  # Use workflow frequency
    
    # FREQ SPECIFIC OUTPUT DIR
    output_dir = Path(base_output_dir).parent / f"{Path(base_output_dir).name}_{target_freq}"
    output_dir = str(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Get market type for hierarchical structure - IGNORE for bin path, we use simple flat structure in separate data dirs
    market_type = data_config.get("market_type", "future")
    
    # Determine exclude fields: all columns except include_fields + symbol + date
    exclude_fields_list = [date_field_name, symbol_field_name]
    # For database data, interval is a column
    if source in ["db", "both"]:
        exclude_fields_list.append('interval')
    exclude_fields = ','.join(exclude_fields_list)
    
    print(f"Target Frequency: {target_freq}")
    print(f"Converting data to {target_freq} frequency from source: {source}...")
    print(f"Output Directory: {output_dir}")
    
    all_data = {}  # Dictionary to hold all symbol data in memory
    mode = "all"
    
    def _symbol_key(symbol: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(symbol).upper())

    expected_symbols = []
    instruments_file = data_convertor.get("instruments_file") or data_config.get("symbols")
    if instruments_file == "<data.symbols>":
        instruments_file = data_config.get("symbols")
    if instruments_file:
        try:
            if not os.path.isabs(instruments_file):
                instruments_file = os.path.join(str(project_root), instruments_file)
            with open(instruments_file, "r") as f:
                inst_data = json.load(f)
                expected_symbols = inst_data.get("symbols", [])
        except Exception as e:
            logger.warning(f"Failed to load instruments file {instruments_file}: {e}")

    def _load_existing_instrument_ends(target_dir: str) -> Dict[str, pd.Timestamp]:
        inst_path = Path(target_dir) / "instruments" / "all.txt"
        if not inst_path.exists():
            return {}
        try:
            df_inst = pd.read_csv(inst_path, sep='\t', header=None, names=['symbol', 'start', 'end'])
            ends = {}
            for _, row in df_inst.iterrows():
                symbol = str(row['symbol']).upper()
                try:
                    ends[symbol] = pd.Timestamp(row['end'])
                except Exception:
                    continue
            return ends
        except Exception as e:
            logger.warning(f"Failed to load existing instruments from {inst_path}: {e}")
            return {}

    existing_end_map = {} if force else _load_existing_instrument_ends(output_dir)
    if force:
        logger.info(f"Force mode enabled: ignoring existing data, will perform full conversion.")

    expected_map = {}
    expected_keys = set()
    for sym in expected_symbols:
        key = _symbol_key(sym)
        if not key:
            continue
        expected_keys.add(key)
        expected_map.setdefault(key, sym)

    # Load data from CSV if source includes csv
    if source in ["csv", "both"]:
        # Recursively find all CSV files in the hierarchical structure
        import glob
        csv_files = glob.glob(os.path.join(input_dir, "**/*.csv"), recursive=True)
        
        symbol_groups = {}
        found_keys = set()
        for csv_file in csv_files:
            # Determine symbol/interval/market_type from path
            # Supported structures:
            # 1) root/ETH_USDT/4h/future/ETH_USDT.csv
            # 2) root/ETHUSDT/ETHUSDT_1m.csv
            rel_path = os.path.relpath(csv_file, input_dir)
            parts = rel_path.split(os.sep)
            if len(parts) >= 4:
                symbol = parts[0]
            elif len(parts) >= 2:
                symbol = parts[0]
            else:
                continue

            symbol_key = _symbol_key(symbol)
            if expected_keys and symbol_key not in expected_keys:
                continue
            if symbol_key:
                found_keys.add(symbol_key)

            # For Qlib symbol, we now just use "ETH_USDT" because we are in a freq-specific dataset
            qlib_symbol = symbol.upper()  # Simple symbol

            if qlib_symbol not in symbol_groups:
                symbol_groups[qlib_symbol] = []

            df = pd.read_csv(csv_file)
            # Resample to target frequency if needed
            if target_freq != "1min":
                df[date_field_name] = pd.to_datetime(df[date_field_name])
                df = df.set_index(date_field_name)
                # Resample OHLCV data appropriately
                agg_dict = {
                    'open': 'first',
                    'high': 'max', 
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }
                
                # Handle funding_rate separately with forward-fill
                # Funding rates settle every 8 hours (not continuous like OHLCV)
                # We need to forward-fill the 8-hour values to finer timeframes
                funding_rate_col = None
                if 'funding_rate' in df.columns:
                    # Save funding_rate column before resampling
                    # Keep the index for proper resampling
                    funding_rate_col = df[['funding_rate']].copy()
                    # Drop duplicate timestamps to avoid resample errors
                    funding_rate_col = funding_rate_col[~funding_rate_col.index.duplicated(keep='last')]
                    funding_rate_col = funding_rate_col.sort_index()
                    # Don't include in agg_dict - handle separately
                    df = df.drop(columns=['funding_rate'])
                
                if 'vwap' in df.columns:
                    # Use weighted average for VWAP if volume exists, else mean
                    if 'volume' in df.columns:
                        # Workaround: Calculate (vwap * volume) -> cum_amount, resample sum, then divide by vol sum.
                        df['amount'] = df['vwap'] * df['volume']
                        agg_dict['amount'] = 'sum'
                    else:
                        agg_dict['vwap'] = 'mean'

                resampled = df.resample(target_freq).agg(agg_dict).dropna().reset_index()
                
                # Post-processing to recover VWAP if we used amount
                if 'amount' in resampled.columns and 'volume' in resampled.columns:
                    resampled['vwap'] = resampled['amount'] / resampled['volume']
                    resampled.drop(columns=['amount'], inplace=True)
                
                # Forward-fill funding_rate from 8-hour native frequency
                # Funding rates don't "aggregate" - they propagate until next settlement
                if funding_rate_col is not None:
                    # Resample funding_rate using forward-fill method
                    funding_resampled = funding_rate_col.resample(target_freq).ffill()
                    # Merge back with OHLCV data
                    resampled = resampled.set_index(date_field_name)
                    resampled = resampled.join(funding_resampled, how='left')
                    resampled = resampled.reset_index()
                     
                df = resampled
                print(f"Resampled {qlib_symbol} to {target_freq}: {len(df)} rows")

            symbol_groups[qlib_symbol].append(df)

        if existing_end_map:
            mode = "update"

        for qlib_symbol, dfs in symbol_groups.items():
            if dfs:
                # Merge and deduplicate data for this symbol
                merged_df = pd.concat(dfs).drop_duplicates(subset=[date_field_name]).sort_values(date_field_name)
                # Convert timestamp to datetime string for Qlib compatibility
                merged_df[date_field_name] = pd.to_datetime(merged_df[date_field_name])
                if existing_end_map:
                    existing_end = existing_end_map.get(qlib_symbol.upper())
                    if existing_end is not None:
                        existing_end = pd.Timestamp(existing_end)
                        merged_df[date_field_name] = pd.to_datetime(merged_df[date_field_name]).dt.tz_localize(None)
                        merged_df = merged_df[merged_df[date_field_name] > existing_end]
                        if merged_df.empty:
                            logger.info(
                                f"Skipping {qlib_symbol} for {target_freq}: no new resampled rows beyond {existing_end}"
                            )
                            continue
                if validate_data_integrity(merged_df, target_freq, date_field=date_field_name):
                    all_data[qlib_symbol] = merged_df  # Store in memory
                    # Log before convert information
                    start_time = merged_df[date_field_name].min()
                    end_time = merged_df[date_field_name].max()
                    total_records = len(merged_df)
                    logger.info(f"Before convert - Symbol: {qlib_symbol}, Start: {start_time}, End: {end_time}, Records: {total_records}")
                else:
                    raise RuntimeError(f"Data integrity validation failed for {qlib_symbol}")

        if expected_keys:
            missing_keys = expected_keys - found_keys
            if missing_keys:
                missing_symbols = [expected_map.get(k, k) for k in sorted(missing_keys)]
                raise RuntimeError(f"Missing CSV data for expected symbols: {missing_symbols}")
    
    # Load data from database if source includes db
    if source in ["db", "both"]:
        db_storage = PostgreSQLStorage(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            database=db_config.get("database", "qlib_crypto"),
            user=db_config.get("user", "crypto_user"),
            password=db_config.get("password", "change_me_in_production"),
            table="ohlcv_data",
            schema={
                'timestamp': 'timestamp',
                'symbol': 'symbol',
                'interval': 'interval',
                'open': 'open_price',
                'high': 'high_price',
                'low': 'low_price',
                'close': 'close_price',
                'volume': 'volume',
                'funding_rate': 'funding_rate',
                'vwap': 'vwap'
            }
        )
        
        # Determine source interval for DB (usually 1m for resampling)
        source_interval = config.get('data_service', {}).get('base_interval', '1m')
        
        # Auto-detect start time for incremental update
        start_time_db = None
        mode = "all"
        
        # Check if calendar exists
        qlib_freq = convert_interval_to_qlib_freq(target_freq)
        calendar_file = Path(output_dir) / "calendars" / f"{qlib_freq}.txt"
        
        if calendar_file.exists() and calendar_file.stat().st_size > 0:
            try:
                # Read last line efficiently
                import subprocess
                last_line = subprocess.check_output(['tail', '-1', str(calendar_file)]).decode().strip()
                if last_line:
                    last_date = pd.Timestamp(last_line)
                    # Fetch from next interval
                    # Add small buffer or exactly one interval? 
                    # get_kline_data is inclusive for start_date.
                    # so if we ask for last_date, we get duplicate.
                    # let's ask for > last_date. DB function uses >=.
                    # We can filter later or add 1 second/interval.
                    start_time_db = (last_date + pd.Timedelta(seconds=1)).isoformat()
                    mode = "update"
                    logger.info(f"Detected existing data up to {last_date}. Running in UPDATE mode starting from {start_time_db}.")
            except Exception as e:
                logger.warning(f"Failed to read existing calendar, falling back to full mode: {e}")
        
        with db_storage:
            symbols = db_storage.get_available_symbols(interval=source_interval)
            
            if not symbols and source_interval == '1m':
                # Try 1h if 1m is empty
                logger.info("No 1m data found, trying 1h...")
                symbols = db_storage.get_available_symbols(interval='1h')
                source_interval = '1h'
            
            logger.info(f"Fetching data for {len(symbols)} symbols from DB (Start: {start_time_db})...")
            
            for symbol in symbols:
                # Pass start_date to incremental fetch
                df = db_storage.get_kline_data(symbol, source_interval, start_time=start_time_db)
                if not df.empty:
                    # Ensure timestamp is datetime
                    df[date_field_name] = pd.to_datetime(df[date_field_name])
                    
                    # Merge funding rates if available
                    try:
                        fr_df = db_storage.get_funding_rates(symbol, start_time=start_time_db)
                        if not fr_df.empty:
                            logger.info(f"{symbol}: Merging {len(fr_df)} funding rate records with OHLCV data")
                            # Use merge_asof to align funding rates (8-hour) with OHLCV timestamps
                            # Direction='backward' means use the most recent past funding rate
                            df = pd.merge_asof(
                                df.sort_values(date_field_name),
                                fr_df[['timestamp', 'funding_rate']].rename(columns={'timestamp': date_field_name}),
                                on=date_field_name,
                                direction='backward'
                            )
                            # Fill any remaining NaN with 0
                            df['funding_rate'] = df['funding_rate'].fillna(0)
                            logger.info(f"{symbol}: Funding rates merged successfully")
                        else:
                            logger.info(f"{symbol}: No funding rate data available, setting to 0")
                            df['funding_rate'] = 0.0
                    except Exception as e:
                        logger.warning(f"{symbol}: Error merging funding rates: {e}. Setting to 0")
                        df['funding_rate'] = 0.0
                    
                    # Resample if target_freq is different from source_interval
                    # 1m -> 1min, 1h -> 60min
                    source_qlib_freq = convert_interval_to_qlib_freq(source_interval)
                    
                    if target_freq != source_qlib_freq:
                        logger.info(f"Resampling {symbol} from {source_qlib_freq} to {target_freq}...")
                        df = df.set_index(date_field_name)
                        # Resample OHLCV data
                        agg_dict = {
                            'open': 'first',
                            'high': 'max', 
                            'low': 'min',
                            'close': 'last',
                            'volume': 'sum'
                        }
                        
                        # Add funding_rate if exists
                        if 'funding_rate' in df.columns:
                            agg_dict['funding_rate'] = 'last'

                        # Handle VWAP for DB path                        
                        if 'vwap' in df.columns:
                            if 'volume' in df.columns:
                                df['amount'] = df['vwap'] * df['volume']
                                agg_dict['amount'] = 'sum'
                            else:
                                agg_dict['vwap'] = 'mean'
                        # Add funding_rate if exists
                        if 'funding_rate' in df.columns:
                            agg_dict['funding_rate'] = 'last'
                            
                        resampled = df.resample(target_freq).agg(agg_dict).dropna().reset_index()
                        
                        # Post-processing to recover VWAP
                        if 'amount' in resampled.columns and 'volume' in resampled.columns:
                             resampled['vwap'] = resampled['amount'] / resampled['volume']
                             resampled.drop(columns=['amount'], inplace=True)
                             
                        df = resampled
                        logger.info(f"Resampled {symbol} to {target_freq}: {len(df)} rows")
                    
                    # Validate data quality
                    quality_stats = db_storage.validate_data_quality(df)
                    if quality_stats['valid']:
                        # Normalize and format symbol to match project directory structure
                        norm_symbol = normalize_symbol(symbol)
                        qlib_symbol = norm_symbol.upper()

                        # Merge with existing data if both sources
                        if qlib_symbol in all_data:
                            # Concatenate and deduplicate
                            combined_df = pd.concat([all_data[qlib_symbol], df]).drop_duplicates(subset=[date_field_name]).sort_values(date_field_name)
                            all_data[qlib_symbol] = combined_df
                        else:
                            all_data[qlib_symbol] = df
                        logger.info(f"Loaded from DB - Symbol: {qlib_symbol} (Raw: {symbol}), Records: {len(df)}")
                    else:
                        logger.warning(f"Data quality issues for {symbol}: {quality_stats['issues']}")
    
    # Now process all data at once
    if not all_data:
        logger.info(f"No new data found for {target_freq}; skipping conversion.")
        _log_conversion_summary(config, source)
        return
    
    # Create temporary directory for CSV files
    with tempfile.TemporaryDirectory() as temp_dir:
        for symbol, df in all_data.items():
            # Use '#' to represent '/' in temp filenames to keep it safe and reconstructible
            filename = symbol.replace("/", "#")
            df.to_csv(os.path.join(temp_dir, f"{filename}.csv"), index=False)

        # Run DumpDataCrypto on the temp dir (skips calendar creation for crypto)
        start_time_convert = time.time()
        dumper = DumpDataCrypto(
            data_path=temp_dir,
            qlib_dir=output_dir,
            freq=target_freq,
            date_field_name=date_field_name,
            symbol_field_name=symbol_field_name,
            exclude_fields=exclude_fields,
            include_fields=','.join(include_fields),
            max_workers=4,
            mode=mode
        )
        # Pass all_data for calendar creation
        dumper.all_data = all_data
        dumper.dump()
        end_time_convert = time.time()
        
        # Count total features (bin files)
        total_features = 0
        for root, dirs, files in os.walk(output_dir):
            total_features += len([f for f in files if f.endswith('.bin')])
        
        elapsed_time = end_time_convert - start_time_convert
        logger.info(f"After convert - Target folder: {output_dir}, Total features: {total_features}, Time taken: {elapsed_time:.2f}s")
    
    print(f"Completed conversion to {target_freq}")
    _log_conversion_summary(config, source)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert cryptocurrency data to Qlib format")
    parser.add_argument("--source", choices=["csv", "db", "both"], 
                       help="Data source: csv (CSV files), db (database), or both. If not specified, uses config data_source.")
    parser.add_argument("--freq", action='append', help="Target frequency (e.g., 15min, 60min). Can be specified multiple times.")
    parser.add_argument("--timeframes", action='append', help="Alias for --freq, supported for data_service compatibility.")
    parser.add_argument("--force", action='store_true', help="Force full re-conversion, ignoring existing data.")
    args = parser.parse_args()
    
    # If --source not provided, let convert_to_qlib() read from config (default: None)
    source = args.source if args.source else None
    
    # Collect all frequencies from both --freq and --timeframes
    freqs = []
    if args.freq:
        freqs.extend(args.freq)
    if args.timeframes:
        freqs.extend(args.timeframes)
    
    # Remove duplicates but keep order
    unique_freqs = []
    for f in freqs:
        if f not in unique_freqs:
            unique_freqs.append(f)
            
    if not unique_freqs:
        # If no freq provided, run once with default from config
        convert_to_qlib(source=source, force=args.force)
    else:
        for f in unique_freqs:
            logger.info(f"Starting conversion task for frequency: {f}")
            convert_to_qlib(source=source, freq=f, force=args.force)
