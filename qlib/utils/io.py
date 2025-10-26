from pathlib import Path
from typing import Optional, Union
import pandas as pd
import numpy as np

def write_parquet(
    df: pd.DataFrame,
    path: Union[str, Path],
    compression: Optional[str] = "snappy"
) -> None:
    """Write DataFrame to Parquet with optional compression
    
    Args:
        df: DataFrame to write
        path: Output file path
        compression: Compression codec (None, 'snappy', 'gzip', 'brotli')
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure index timezone is preserved
    df = df.copy()
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    df.to_parquet(
        path,
        compression=compression,
        index=True
    )

def read_parquet(path: Union[str, Path]) -> pd.DataFrame:
    """Read DataFrame from Parquet with index

    Args:
        path: Input file path

    Returns:
        DataFrame with datetime index
    """
    df = pd.read_parquet(path)
    # Restore timezone if needed
    if hasattr(df.index, 'tz') and df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    # Infer and set frequency if possible, but only for datetime-like indices
    if hasattr(df.index, 'dtype') and hasattr(df.index.dtype, 'type') and issubclass(df.index.dtype.type, (pd.Timestamp, np.datetime64)):
        try:
            inferred_freq = pd.infer_freq(df.index)
            if inferred_freq is not None:
                df.index.freq = pd.tseries.frequencies.to_offset(inferred_freq)
        except (TypeError, ValueError):
            # Skip frequency inference for non-datetime or irregular indices
            pass
    return df
