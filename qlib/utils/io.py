from pathlib import Path
from typing import Optional, Union
import pandas as pd

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
    return pd.read_parquet(path)
