import os
import pandas as pd
import tempfile
import numpy as np
from pathlib import Path
from typing import List
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from loguru import logger
from qlib.utils import fname_to_code, code_to_fname

from config_manager import ConfigManager
from dump_bin import DumpDataAll  # Import DumpDataAll for binary conversion

class DumpDataCrypto(DumpDataAll):
    """Custom dumper for crypto data that skips calendar creation since crypto markets are 24/7."""
    
    def get_symbol_from_file(self, file_path: Path) -> str:
        """Convert file path to symbol, handling crypto naming conventions."""
        # file_path.stem is like 'BTC_USDT', we need to convert to 'BTCUSDT'
        symbol_with_underscore = file_path.stem.strip().lower()
        # Remove underscores to match qlib's expected format
        symbol = symbol_with_underscore.replace('_', '')
        return fname_to_code(symbol)
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol by removing slashes and underscores."""
        return symbol.replace('/', '').replace('_', '').lower()
    
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
            code = fname_to_code(self._normalize_symbol(raw_symbol))
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

        # features save dir
        features_dir = self._features_dir.joinpath(code_to_fname(code).lower())
        features_dir.mkdir(parents=True, exist_ok=True)
        
        # For crypto, save data directly without calendar alignment
        self._data_to_bin_crypto(df, features_dir)
    
    def _data_to_bin_crypto(self, df: pd.DataFrame, features_dir: Path):
        """Save data to binary format for crypto using calendar alignment like qlib."""
        if df.empty:
            logger.warning(f"{features_dir.name} data is None or empty")
            return
        if not self._calendars_list:
            logger.warning("calendar_list is empty")
            return
        
        # Align data with calendar
        _df = self.data_merge_calendar(df, self._calendars_list)
        if _df.empty:
            logger.warning(f"{features_dir.name} data is not in calendars")
            return
            
        # Get dump fields (exclude timestamp as it's the index)
        dump_fields = self.get_dump_fields(_df.columns)
        dump_fields = [f for f in dump_fields if f != self.date_field_name]
        
        for field in dump_fields:
            if field not in _df.columns:
                continue
            
            # Get the start index for this data
            start_index = self.get_datetime_index(_df.dropna(subset=[field]), self._calendars_list)
            
            # Fill NaN values with 0 (or appropriate default)
            field_data = _df[field].fillna(0).values
            
            # Save in qlib format: [start_index, values...]
            bin_path = features_dir.joinpath(f"{field}.{self.freq}.bin")
            data_array = np.concatenate([[start_index], field_data]).astype(np.float32)
            data_array.astype("<f").tofile(str(bin_path))
    
    def dump(self):
        self._get_all_date()
        # For crypto, create a calendar file with all collected timestamps
        self._dump_calendars_crypto()
        self._dump_instruments()
        self._dump_features()
    
    def _dump_calendars_crypto(self):
        """Create calendar file for crypto data using all collected timestamps."""
        logger.info("start dump calendars for crypto......")
        # Use the collected timestamps from _get_all_date
        if self._kwargs["all_datetime_set"]:
            self._calendars_list = sorted(map(pd.Timestamp, self._kwargs["all_datetime_set"]))
            self.save_calendars(self._calendars_list)
        else:
            logger.warning("No datetime data found for calendar creation")
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

# Update input_dir and output_dir to use centralized parameters
input_dir = config.get("data", {}).get("csv_data_dir", "data/klines")
output_dir = os.path.abspath(config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto"))

def validate_data_integrity(df, freq):
    """
    Validate data integrity by checking for gaps and ensuring correct timestamps.

    Args:
        df (pd.DataFrame): DataFrame containing OHLCV data.
        freq (str): Frequency string for pd.date_range (e.g., "15T" for 15 minutes).

    Returns:
        bool: True if data is valid, False otherwise.
    """
    if df.empty:
        return False
    # Convert timestamp to datetime
    df_copy = df.copy()
    df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
    # Check for missing timestamps
    expected_intervals = pd.date_range(
        start=df_copy["timestamp"].min(),
        end=df_copy["timestamp"].max(),
        freq=freq
    )
    actual_intervals = df_copy["timestamp"]
    return set(expected_intervals).issubset(set(actual_intervals))


def convert_to_qlib():
    """
    Convert OHLCV data from CSV format to Qlib-compatible binary format.
    """
    # Get configuration parameters
    data_config = config.get("data", {})
    data_convertor = config.get("data_convertor", {})
    data_collection = config.get("data_collection", {})
    
    input_dir = data_config.get("csv_data_dir", "data/klines")
    output_dir = os.path.abspath(data_config.get("bin_data_dir", "data/qlib_data"))
    os.makedirs(output_dir, exist_ok=True)
    
    # Get interval from data_collection and convert to qlib freq
    interval = data_collection.get("interval", "1m")
    freq = config_manager._convert_ccxt_freq_to_qlib(interval)
    
    # Get convertor parameters
    date_field_name = data_convertor.get("date_field_name", "timestamp")
    include_fields = data_convertor.get("include_fields", ["open", "high", "low", "close", "volume"])
    symbol_field_name = "symbol"  # Assuming default, can be added to config if needed
    
    # Determine exclude fields: all columns except include_fields + symbol + date
    exclude_fields_list = [date_field_name, symbol_field_name]
    if 'interval' in pd.read_csv(os.path.join(input_dir, os.listdir(input_dir)[0], os.listdir(os.path.join(input_dir, os.listdir(input_dir)[0]))[0])).columns:
        exclude_fields_list.append('interval')
    exclude_fields = ','.join(exclude_fields_list)
    
    all_data = {}  # Dictionary to hold all symbol data in memory
    
    for symbol_dir in os.listdir(input_dir):
        symbol_path = os.path.join(input_dir, symbol_dir)
        if os.path.isdir(symbol_path):
            symbol_data = []
            for file in os.listdir(symbol_path):
                if file.endswith(".csv"):
                    df = pd.read_csv(os.path.join(symbol_path, file))
                    symbol_data.append(df)
            if symbol_data:
                # Merge and deduplicate data for this symbol
                merged_df = pd.concat(symbol_data).drop_duplicates(subset=[date_field_name]).sort_values(date_field_name)
                # Convert timestamp to datetime string for Qlib compatibility
                merged_df[date_field_name] = pd.to_datetime(merged_df[date_field_name])
                if validate_data_integrity(merged_df, freq):
                    all_data[symbol_dir] = merged_df  # Store in memory
                else:
                    print(f"Data integrity validation failed for {symbol_dir}")

    # Now process all data at once
    if not all_data:
        print("No valid data found.")
        return

    # Create temporary directory for CSV files
    with tempfile.TemporaryDirectory() as temp_dir:
        for symbol, df in all_data.items():
            df.to_csv(os.path.join(temp_dir, f"{symbol}.csv"), index=False)

        # Run DumpDataCrypto on the temp dir (skips calendar creation for crypto)
        dumper = DumpDataCrypto(
            data_path=temp_dir,
            qlib_dir=output_dir,
            freq=freq,
            date_field_name=date_field_name,
            symbol_field_name=symbol_field_name,
            exclude_fields=exclude_fields,
            include_fields=','.join(include_fields),
            max_workers=4
        )
        dumper.dump()

if __name__ == "__main__":
    convert_to_qlib()
