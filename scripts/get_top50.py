import ccxt
import pandas as pd
from datetime import datetime, timezone
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CONFIG_PATH = "config/top50_symbols.json"

def get_okx_funding_top50() -> list[str]:
    """
    Fetch all OKX perpetual swaps funding rates via CCXT, rank by absolute funding rate, return top 50 symbols.
    
    Returns:
        List of symbol strings like ['BTC/USDT', 'ETH/USDT', ...]
    """
    try:
        exchange = ccxt.okx()
        # Fetch funding rates for all perpetual swaps
        funding_rates = exchange.fetch_funding_rates()
        
        if not funding_rates:
            logger.error("No funding rate data received from OKX via CCXT")
            return []
        
        # Convert to DataFrame
        data = []
        for symbol, info in funding_rates.items():
            if symbol.endswith(':USDT') or '/USDT' in symbol:  # Perpetual swaps
                data.append({
                    'symbol': symbol,
                    'funding_rate': info.get('fundingRate', 0),
                    'next_funding_time': info.get('nextFundingTime', 0)
                })
        
        if not data:
            logger.error("No perpetual swap funding rates found")
            return []
            
        df = pd.DataFrame(data)
        logger.info(f"Fetched {len(df)} funding rate records")
        
        # Convert funding_rate to absolute float
        df['funding_rate'] = df['funding_rate'].astype(float).abs()
        
        # Sort by absolute funding rate descending
        df = df.sort_values('funding_rate', ascending=False).head(50)
        
        # Extract symbols (CCXT format is BTC/USDT:USDT for perpetuals, but we want BTC/USDT)
        symbols = []
        for sym in df['symbol']:
            if ':USDT' in sym:
                base = sym.split(':')[0]
                symbols.append(f"{base}/USDT")
            else:
                symbols.append(sym)
        
        logger.info(f"Selected top 50 symbols by funding rate: {symbols[:5]}...")
        return symbols
        
    except Exception as e:
        logger.error(f"Failed to fetch funding rates via CCXT: {e}")
        return []

def save_symbols(symbols: list[str], path: str = CONFIG_PATH):
    """
    Save symbols list to JSON file.
    
    Args:
        symbols: List of symbol strings
        path: File path to save to
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    data = {
        "symbols": symbols,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(symbols)
    }
    
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(symbols)} symbols to {path}")
    except Exception as e:
        logger.error(f"Failed to save symbols to {path}: {e}")

def load_symbols(path: str = CONFIG_PATH) -> list[str]:
    """
    Load symbols list from JSON file.
    
    Args:
        path: File path to load from
        
    Returns:
        List of symbol strings, or empty list if file not found/error
    """
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        symbols = data.get('symbols', [])
        logger.info(f"Loaded {len(symbols)} symbols from {path}")
        return symbols
    except FileNotFoundError:
        logger.warning(f"Symbols file not found: {path}")
        return []
    except Exception as e:
        logger.error(f"Failed to load symbols from {path}: {e}")
        return []

if __name__ == '__main__':
    logger.info("Starting top 50 symbol selection")
    
    # Activate qlib environment reminder
    print("Reminder: Ensure 'conda activate qlib' before running")
    
    symbols = get_okx_funding_top50()
    if symbols:
        save_symbols(symbols)
        print(f"Successfully updated top 50 symbols: {symbols[:5]}...")
    else:
        print("Failed to fetch symbols")
        exit(1)
