import pandas as pd
from pathlib import Path
from loguru import logger

def format_and_resample(input_file, formatted_dir):
    """
    Format 1h data and derive 4h/1d data with unique symbol names.
    """
    df = pd.read_csv(input_file)
    df['date'] = pd.to_datetime(df['date'])
    
    # Original stem like ETH_USDT_1h_future
    base_symbol = input_file.stem

    # Ensure vwap exists for Alpha158 compatibility
    if 'vwap' not in df.columns:
        logger.warning(f"vwap missing in {input_file.name}, using close as fallback.")
        df['vwap'] = df['close']
    
    # 1. Save Formatted 1h
    df_1h = df.copy()
    symbol_1h = base_symbol.upper()
    df_1h['symbol'] = symbol_1h
    df_1h['weekday'] = df_1h['date'].dt.weekday.astype(float)
    df_1h['hour'] = df_1h['date'].dt.hour.astype(float)
    df_1h.to_csv(formatted_dir / "1h" / f"{symbol_1h}.csv", index=False)
    logger.info(f"Saved formatted 1h with time features: {symbol_1h}")

    # 2. Resample to 4h
    df_4h = df.set_index('date').resample('4h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'vwap': 'mean'
    }).dropna()
    df_4h['weekday'] = df_4h.index.weekday.astype(float)
    df_4h['hour'] = df_4h.index.hour.astype(float)
    symbol_4h = base_symbol.upper().replace("_1H_", "_4H_")
    df_4h['symbol'] = symbol_4h
    df_4h.reset_index().to_csv(formatted_dir / "4h" / f"{symbol_4h}.csv", index=False)
    logger.info(f"Saved resampled 4h with time features: {symbol_4h}")

    # 3. Resample to 1d
    df_1d = df.set_index('date').resample('1d').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'vwap': 'mean'
    }).dropna()
    df_1d['weekday'] = df_1d.index.weekday.astype(float)
    df_1d['hour'] = df_1d.index.hour.astype(float) # In 1d, this is usually constant but kept for consistency
    symbol_1d = base_symbol.upper().replace("_1H_", "_1D_")
    df_1d['symbol'] = symbol_1d
    df_1d.reset_index().to_csv(formatted_dir / "1d" / f"{symbol_1d}.csv", index=False)
    logger.info(f"Saved resampled 1d with time features: {symbol_1d}")

def main():
    source_dir = Path("data/klines")
    formatted_dir = Path("data/formatted")
    
    for freq in ["1h", "4h", "1d"]:
        (formatted_dir / freq).mkdir(parents=True, exist_ok=True)
        
    files = list(source_dir.glob("*_1h_future.csv"))
    
    if not files:
        logger.error("No 1h CSV files found in data/klines.")
        return

    for f in files:
        format_and_resample(f, formatted_dir)

if __name__ == "__main__":
    main()
