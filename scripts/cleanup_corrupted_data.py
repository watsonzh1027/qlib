import os
import pandas as pd
import glob
from qlib.utils.logging_config import setup_logging, startlog

# Setup logging
logger = startlog(name="cleanup_corrupted_data")

def cleanup_csv_files(base_dir="data/klines"):
    """
    Scans base_dir for CSV files and removes rows where the 'timestamp' column is empty or invalid.
    """
    logger.info(f"Starting cleanup of corrupted CSV files in {base_dir}...")
    
    csv_files = glob.glob(os.path.join(base_dir, "**/*.csv"), recursive=True)
    logger.info(f"Found {len(csv_files)} CSV files to check")
    
    cleaned_count = 0
    total_rows_removed = 0
    
    for filepath in csv_files:
        try:
            # Read first column to check for empty timestamps efficiently
            # We use pandas for simplicity but read_csv with usecols to save memory
            df = pd.read_csv(filepath)
            
            if df.empty:
                continue
                
            original_len = len(df)
            
            # Remove rows where timestamp is null or empty string
            # Also handle if timestamp column starts with a comma (malformed line)
            df = df[df['timestamp'].notnull()]
            df = df[df['timestamp'].astype(str).str.strip() != '']
            
            rows_removed = original_len - len(df)
            
            if rows_removed > 0:
                logger.warning(f"File {filepath}: Removed {rows_removed} corrupted rows")
                # Save back the cleaned file
                df.to_csv(filepath, index=False)
                cleaned_count += 1
                total_rows_removed += rows_removed
            else:
                logger.debug(f"File {filepath}: OK")
                
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            
    logger.info(f"Cleanup complete. Repaired {cleaned_count} files, removed {total_rows_removed} total corrupted rows.")

if __name__ == "__main__":
    cleanup_csv_files()
