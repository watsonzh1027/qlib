import os
import pandas as pd
import tempfile
from config_manager import ConfigManager
from dump_bin import DumpDataAll  # Import DumpDataAll for binary conversion

"""
Convert OHLCV data from CSV format to Qlib-compatible binary format.

This module processes crypto OHLCV data organized by symbol directories,
merges CSV files, validates integrity, and converts to Qlib binary format
(instruments and features only, no calendars for continuous trading data).
Frequency is dynamically set from the 'interval' column (e.g., "15m").
"""

# Load configuration
config = ConfigManager("config/workflow.json").load_config()

# Update input_dir and output_dir to use centralized parameters
input_dir = config.get("data", {}).get("csv_data_dir", "data/klines")
output_dir = os.path.abspath(config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto"))

def validate_data_integrity(df):
    """
    Validate data integrity by checking for gaps and ensuring correct timestamps.

    Args:
        df (pd.DataFrame): DataFrame containing OHLCV data.

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
        freq="15T"
    )
    actual_intervals = df_copy["timestamp"]
    return set(expected_intervals).issubset(set(actual_intervals))


def convert_to_qlib():
    """
    Convert OHLCV data from CSV format to Qlib-compatible binary format.
    """
    input_dir = config.get("data", {}).get("csv_data_dir", "data/klines")
    output_dir = os.path.abspath(config.get("data", {}).get("bin_data_dir", "data/qlib_data/crypto"))
    os.makedirs(output_dir, exist_ok=True)
    all_data = {}  # Dictionary to hold all symbol data in memory
    freq = None
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
                merged_df = pd.concat(symbol_data).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
                # Convert timestamp to datetime string for Qlib compatibility
                merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp'])
                if validate_data_integrity(merged_df):
                    # Extract freq from interval column (assume consistent across symbols)
                    if freq is None and 'interval' in merged_df.columns:
                        freq = str(merged_df['interval'].iloc[0])
                    all_data[symbol_dir] = merged_df  # Store in memory
                else:
                    print(f"Data integrity validation failed for {symbol_dir}")

    # Now process all data at once
    if not all_data:
        print("No valid data found.")
        return

    if freq is None:
        freq = "high"  # Default if no interval found

    # Create temporary directory for CSV files
    with tempfile.TemporaryDirectory() as temp_dir:
        for symbol, df in all_data.items():
            df.to_csv(os.path.join(temp_dir, f"{symbol}.csv"), index=False)

        # Run DumpDataAll on the temp dir
        dumper = DumpDataAll(
            data_path=temp_dir,
            qlib_dir=output_dir,
            freq=freq,
            date_field_name="timestamp",
            symbol_field_name="symbol",
            exclude_fields="interval,symbol",
            max_workers=4
        )
        dumper.dump()

if __name__ == "__main__":
    convert_to_qlib()
