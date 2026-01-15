import os
import sys
import pandas as pd
import tempfile
import numpy as np
import time
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

# Add project root to Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.config_manager import ConfigManager
from scripts.dump_bin import DumpDataAll  # Import DumpDataAll for binary conversion


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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all_data = {}  # Will be set externally
    
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
        
        # Check for excessive NaN values before processing
        nan_ratio = _df.isnull().mean().mean()
        logger.info(f"{features_dir.name}: NaN ratio = {nan_ratio:.3f}")
        
        if nan_ratio > 0.5:  # If more than 50% NaN, skip this symbol
            logger.warning(f"{features_dir.name}: Too many NaN values ({nan_ratio:.3f}), skipping")
            return
        
        # Fill NaN values with forward/backward fill, then interpolation, then 0
        _df = _df.ffill().bfill().interpolate(method='linear').fillna(0)
        
        # Reindex to calendar timestamps to align with qlib expectations
        # Load calendar
        calendar_path = self._features_dir.parent / 'calendars' / f'{self.freq}.txt'
        if calendar_path.exists():
            with open(calendar_path, 'r') as f:
                calendar_timestamps = [pd.Timestamp(line.strip()) for line in f.readlines()]
            
            # Convert data index to naive datetime (remove timezone) to match calendar
            _df.index = _df.index.tz_localize(None)
            
            # Reindex data to calendar timestamps
            _df = _df.reindex(calendar_timestamps, method='nearest')
            logger.info(f"{features_dir.name}: Reindexed to {len(calendar_timestamps)} calendar timestamps, data shape: {_df.shape}")
        
        # Get dump fields (exclude timestamp as it's the index)
        dump_fields = self.get_dump_fields(_df.columns)
        dump_fields = [f for f in dump_fields if f != self.date_field_name]
        
        for field in dump_fields:
            if field not in _df.columns:
                continue
            
            # Get the start index for this data (use the index positions)
            start_index = 0  # Start from beginning since no calendar alignment
            
            # Fill NaN values with forward/backward fill, then interpolation, then 0
            field_data = _df[field].ffill().bfill().interpolate(method='linear').fillna(0).values
            
            # Save in qlib format: [start_index, values...]
            # Qlib's FileFeatureStorage forces lower() on field and freq
            bin_path = features_dir.joinpath(f"{field.lower()}.{self.freq.lower()}.bin")
            data_array = np.concatenate([[start_index], field_data]).astype(np.float32)
            data_array.astype("<f").tofile(str(bin_path))
            logger.info(f"Saved {field} to {bin_path}, size: {len(data_array)}")
    
    def dump(self):
        # For crypto, create a simple calendar since markets are 24/7
        self._dump_calendars_crypto()
        self._dump_instruments_crypto()
        self._dump_features()
    
    def _dump_instruments_crypto(self):
        """Create instruments file for crypto data using all_data."""
        logger.info("start dump instruments for crypto......")
        date_range_list = []
        
        for symbol, df in self.all_data.items():
            if not df.empty and self.date_field_name in df.columns:
                timestamps = pd.to_datetime(df[self.date_field_name])
                start_time = timestamps.min()
                end_time = timestamps.max()
                begin_time = self._format_datetime(start_time)
                end_time = self._format_datetime(end_time)
                # Store symbol as is (it should already be normalized)
                inst_fields = [symbol, begin_time, end_time]
                date_range_list.append(f"{self.INSTRUMENTS_SEP.join(inst_fields)}")
        
        self.save_instruments(date_range_list)
        logger.info("end of instruments dump.\n")
    
    def _dump_calendars_crypto(self):
        """Create calendar file for crypto data using data from memory."""
        logger.info("start dump calendars for crypto......")
        
        # use dates from memory
        all_dates = []
        for qlib_symbol, df in self.all_data.items():
            all_dates.extend(df[self.date_field_name].tolist())
        
        if not all_dates:
            logger.warning("No data found to generate calendar")
            return
            
        all_dates = sorted(list(set(pd.to_datetime(all_dates))))
        self._calendars_list = all_dates
        
        # Save to target freq
        qlib_freq = convert_interval_to_qlib_freq(self.freq)
        self._calendars_dir.mkdir(parents=True, exist_ok=True)
        calendar_path = self._calendars_dir.joinpath(f"{qlib_freq}.txt")
        with open(calendar_path, "w") as f:
            for d in self._calendars_list:
                f.write(f"{d}\n")
                
        logger.info(f"Created calendar {qlib_freq} with {len(self._calendars_list)} timestamps")
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


def convert_to_qlib(source: str = None):
    """
    Convert OHLCV data from CSV and/or database format to Qlib-compatible binary format.
    
    Args:
        source: Data source - "csv", "db", or "both". If None, uses config data_source.
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
    output_dir = os.path.abspath(data_config.get("bin_data_dir", "data/qlib_data"))
    os.makedirs(output_dir, exist_ok=True)
    
    # Get convertor parameters
    date_field_name = data_convertor.get("date_field_name", "timestamp")
    include_fields = data_convertor.get("include_fields", ["open", "high", "low", "close", "volume"])
    symbol_field_name = "symbol"  # Assuming default, can be added to config if needed
    
    # Get interval from config and convert to qlib frequency
    interval = data_collection.get("interval", "1h")
    target_freq = config.get("workflow", {}).get("frequency", "60min")  # Use workflow frequency
    
    # Determine exclude fields: all columns except include_fields + symbol + date
    exclude_fields_list = [date_field_name, symbol_field_name]
    # For database data, interval is a column
    if source in ["db", "both"]:
        exclude_fields_list.append('interval')
    exclude_fields = ','.join(exclude_fields_list)
    
    print(f"Target Frequency: {target_freq}")
    print(f"Converting data to {target_freq} frequency from source: {source}...")
    
    all_data = {}  # Dictionary to hold all symbol data in memory
    
    # Load data from CSV if source includes csv
    if source in ["csv", "both"]:
        # Recursively find all CSV files in the hierarchical structure
        import glob
        csv_files = glob.glob(os.path.join(input_dir, "**/*.csv"), recursive=True)
        
        symbol_groups = {}
        for csv_file in csv_files:
            # Determine symbol/interval/market_type from path
            # Expected structure: root/ETH_USDT/4h/future/ETH_USDT.csv
            rel_path = os.path.relpath(csv_file, input_dir)
            parts = rel_path.split(os.sep)
            if len(parts) >= 4:
                symbol = parts[0]
                # Use target_freq for the qlib instrument name to match expectation
                market_type = parts[2]
                qlib_symbol = f"{symbol.upper()}/{target_freq}/{market_type.upper()}"
                
                if qlib_symbol not in symbol_groups:
                    symbol_groups[qlib_symbol] = []
                
                df = pd.read_csv(csv_file)
                # Resample to target frequency if needed
                if target_freq != "1min":
                    df[date_field_name] = pd.to_datetime(df[date_field_name])
                    df = df.set_index(date_field_name)
                    # Resample OHLCV data appropriately
                    resampled = df.resample(target_freq).agg({
                        'open': 'first',
                        'high': 'max', 
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                    df = resampled.reset_index()
                    print(f"Resampled {qlib_symbol} to {target_freq}: {len(df)} rows")
                
                symbol_groups[qlib_symbol].append(df)

        for qlib_symbol, dfs in symbol_groups.items():
            if dfs:
                # Merge and deduplicate data for this symbol
                merged_df = pd.concat(dfs).drop_duplicates(subset=[date_field_name]).sort_values(date_field_name)
                # Convert timestamp to datetime string for Qlib compatibility
                merged_df[date_field_name] = pd.to_datetime(merged_df[date_field_name])
                if validate_data_integrity(merged_df, target_freq, date_field=date_field_name):
                    all_data[qlib_symbol] = merged_df  # Store in memory
                    # Log before convert information
                    start_time = merged_df[date_field_name].min()
                    end_time = merged_df[date_field_name].max()
                    total_records = len(merged_df)
                    logger.info(f"Before convert - Symbol: {qlib_symbol}, Start: {start_time}, End: {end_time}, Records: {total_records}")
                else:
                    print(f"Data integrity validation failed for {qlib_symbol}")
    
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
                'volume': 'volume'
            }
        )
        with db_storage:
            symbols = db_storage.get_available_symbols(interval=interval)
            for symbol in symbols:
                df = db_storage.get_kline_data(symbol, interval)
                if not df.empty:
                    # Ensure timestamp is datetime
                    df[date_field_name] = pd.to_datetime(df[date_field_name])
                    # Validate data quality
                    quality_stats = db_storage.validate_data_quality(df)
                    if quality_stats['valid']:
                        # Merge with existing data if both sources
                        if symbol in all_data:
                            # Concatenate and deduplicate
                            combined_df = pd.concat([all_data[symbol], df]).drop_duplicates(subset=[date_field_name]).sort_values(date_field_name)
                            all_data[symbol] = combined_df
                        else:
                            all_data[symbol] = df
                        logger.info(f"Loaded from DB - Symbol: {symbol}, Records: {len(df)}")
                    else:
                        logger.warning(f"Data quality issues for {symbol}: {quality_stats['issues']}")
    
    # Now process all data at once
    if not all_data:
        print(f"No valid data found for {target_freq}.")
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
            max_workers=4
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert cryptocurrency data to Qlib format")
    parser.add_argument("--source", choices=["csv", "db", "both"], 
                       help="Data source: csv (CSV files), db (database), or both. If not specified, uses config data_source.")
    args = parser.parse_args()
    
    source = args.source if args.source else 'db'
    convert_to_qlib(source=source)
