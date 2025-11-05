import os
import pandas as pd
from config_manager import ConfigManager

# Load configuration
config = ConfigManager("config/workflow.json").load_config()

# Update input_dir and output_dir to use centralized parameters
input_dir = config.get("input_dir", "data/klines")
output_dir = config.get("output_dir", "data/qlib_data")

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
    # Check for missing timestamps
    expected_intervals = pd.date_range(
        start=pd.to_datetime(df["timestamp"].min(), unit="s"),
        end=pd.to_datetime(df["timestamp"].max(), unit="s"),
        freq="15T"
    )
    actual_intervals = pd.to_datetime(df["timestamp"], unit="s")
    return set(expected_intervals).issubset(set(actual_intervals))


def convert_to_qlib(input_dir="data/klines", output_dir="data/qlib_data"):
    """
    Convert OHLCV data from Parquet format to Qlib-compatible binary format.

    Args:
        input_dir (str): Directory containing OHLCV Parquet files.
        output_dir (str): Directory to save Qlib-compatible data.
    """
    os.makedirs(output_dir, exist_ok=True)
    instruments_dir = os.path.join(output_dir, "instruments")
    os.makedirs(instruments_dir, exist_ok=True)  # Ensure the instruments directory exists

    instruments = []

    for symbol_dir in os.listdir(input_dir):
        symbol_path = os.path.join(input_dir, symbol_dir)
        if os.path.isdir(symbol_path):
            all_data = []
            for file in os.listdir(symbol_path):
                if file.endswith(".parquet"):
                    df = pd.read_parquet(os.path.join(symbol_path, file))
                    all_data.append(df)
            if all_data:
                # Merge and deduplicate data
                merged_df = pd.concat(all_data).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
                if validate_data_integrity(merged_df):
                    merged_df.to_parquet(f"{output_dir}/{symbol_dir}.parquet", index=False)
                    instruments.append(symbol_dir)
                else:
                    print(f"Data integrity validation failed for {symbol_dir}")

    # Generate instruments registry
    with open(f"{instruments_dir}/all.txt", "w") as f:
        f.write("\n".join(instruments))
