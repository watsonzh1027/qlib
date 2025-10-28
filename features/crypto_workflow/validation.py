from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

def validate_ohlcv(df: pd.DataFrame) -> Tuple[bool, Dict[str, List[int]]]:
    """Validate OHLCV data quality

    Args:
        df: DataFrame with OHLCV columns

    Returns:
        (valid, error_rows) tuple where valid is boolean and error_rows is dict mapping error types to row indices
    """
    errors: Dict[str, List[int]] = {}
    
    # Check required columns
    required = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required):
        missing = [col for col in required if col not in df.columns]
        return False, {'missing_columns': missing}
    
    # Check for NaN values
    nan_rows = df[required].isna().any(axis=1)
    if nan_rows.any():
        errors['nan_values'] = nan_rows[nan_rows].index.tolist()
    
    # Validate OHLC relationships
    invalid_hl = df[df['high'] < df['low']].index.tolist()
    if invalid_hl:
        errors['high_low_invalid'] = invalid_hl
        
    invalid_open = df[~df['open'].between(df['low'], df['high'])].index.tolist()
    if invalid_open:
        errors['open_range_invalid'] = invalid_open
        
    invalid_close = df[~df['close'].between(df['low'], df['high'])].index.tolist()
    if invalid_close:
        errors['close_range_invalid'] = invalid_close
    
    # Validate volume
    invalid_volume = df[df['volume'] < 0].index.tolist()
    if invalid_volume:
        errors['negative_volume'] = invalid_volume
    
    return len(errors) == 0, errors

def validate_features(df: pd.DataFrame, max_null_pct: float = 0.05) -> Tuple[bool, Dict[str, List[str]]]:
    """Validate feature data quality

    Args:
        df: DataFrame with feature columns
        max_null_pct: Maximum allowed percentage of null values per column

    Returns:
        (valid, error_cols) tuple where valid is boolean and error_cols maps error types to column names
    """
    errors: Dict[str, List[str]] = {}
    
    # Check for constant columns
    constant_cols = [col for col in df.columns 
                    if df[col].nunique() == 1]
    if constant_cols:
        errors['constant_columns'] = constant_cols
    
    # Check for columns with too many nulls
    null_pcts = df.isnull().mean()
    high_null_cols = null_pcts[null_pcts > max_null_pct].index.tolist()
    if high_null_cols:
        errors['high_null_columns'] = high_null_cols
    
    # Check for infinite values
    inf_cols = [col for col in df.columns 
                if np.isinf(df[col]).any()]
    if inf_cols:
        errors['infinite_columns'] = inf_cols
        
    return len(errors) == 0, errors
