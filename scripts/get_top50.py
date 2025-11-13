import ccxt
import pandas as pd
from datetime import datetime, timezone, timedelta
import json
import os
import logging
import requests
import time
from typing import List, Optional, Dict, Any
from scripts.config_manager import ConfigManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CONFIG_PATH = "config/top50_symbols.json"
INSTRUMENTS_PATH = "config/instruments.json"
CACHE_DIR = "cache"
COINGECKO_CACHE_FILE = os.path.join(CACHE_DIR, "coingecko_marketcap.json")
OKX_CACHE_FILE = os.path.join(CACHE_DIR, "okx_contracts.json")

# Cache expiration times
COINGECKO_CACHE_EXPIRY = timedelta(hours=1)
OKX_CACHE_EXPIRY = timedelta(minutes=15)

# Load configuration
config = ConfigManager("config/workflow.json").load_config()

# Update CONFIG_PATH and INSTRUMENTS_PATH to use centralized parameters
CONFIG_PATH = config.get("top50_symbols_path", CONFIG_PATH)
INSTRUMENTS_PATH = config.get("instruments_path", INSTRUMENTS_PATH)

def _load_cache(cache_file: str, expiry: timedelta) -> Optional[Dict[str, Any]]:
    """Load cached data if it exists and is not expired."""
    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)

        cached_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01T00:00:00'))
        if datetime.now(timezone.utc) - cached_time < expiry:
            logger.info(f"Using cached data from {cache_file}")
            return data
        else:
            logger.info(f"Cache expired for {cache_file}")
            return None
    except Exception as e:
        logger.warning(f"Failed to load cache from {cache_file}: {e}")
        return None

def _save_cache(cache_file: str, data: Dict[str, Any]) -> None:
    """Save data to cache file."""
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    data['timestamp'] = datetime.now(timezone.utc).isoformat()

    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved cache to {cache_file}")
    except Exception as e:
        logger.error(f"Failed to save cache to {cache_file}: {e}")

def get_marketcap_top50(top_n: int = 50) -> List[str]:
    """
    Fetch top N cryptocurrencies by market capitalization from CoinGecko API.

    Args:
        top_n: Number of top coins to return

    Returns:
        List of uppercase symbol strings like ['BTC', 'ETH', ...]
    """
    # Try cache first
    cached = _load_cache(COINGECKO_CACHE_FILE, COINGECKO_CACHE_EXPIRY)
    if cached:
        symbols = cached.get('symbols', [])[:top_n]
        if symbols:
            return symbols

    # Fetch from API
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': top_n,
        'page': 1,
        'sparkline': False
    }

    try:
        logger.info("Fetching market cap data from CoinGecko API")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        symbols = [coin['symbol'].upper() for coin in data]

        # Cache the results
        cache_data = {'symbols': symbols}
        _save_cache(COINGECKO_CACHE_FILE, cache_data)

        logger.info(f"Fetched top {len(symbols)} coins by market cap: {symbols[:5]}...")
        return symbols

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch market cap data from CoinGecko: {e}")
        # Return cached data if available, even if expired
        if cached:
            symbols = cached.get('symbols', [])[:top_n]
            logger.warning("Using expired cached data due to API failure")
            return symbols
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching market cap data: {e}")
        return []

def get_okx_swap_symbols() -> List[str]:
    """
    Discover all available OKX perpetual swap contracts.

    Returns:
        List of contract names in format "SYMBOL-USDT-SWAP"
    """
    # Try cache first
    cached = _load_cache(OKX_CACHE_FILE, OKX_CACHE_EXPIRY)
    if cached:
        contracts = cached.get('contracts', [])
        if contracts:
            return contracts

    try:
        logger.info("Fetching OKX perpetual swap contracts")
        exchange = ccxt.okx()

        # Get all markets
        markets = exchange.load_markets()

        # Filter for USDT settled perpetual swaps
        contracts = []
        for symbol, market in markets.items():
            if (market.get('type') == 'swap' and
                market.get('settle') == 'USDT'):
                # Convert CCXT format "BTC/USDT:USDT" to "BTC-USDT-SWAP"
                if symbol.endswith('/USDT:USDT'):
                    base_symbol = symbol[:-10]  # Remove '/USDT:USDT'
                    contract_name = f"{base_symbol}-USDT-SWAP"
                    contracts.append(contract_name)

        # Cache the results
        cache_data = {'contracts': contracts}
        _save_cache(OKX_CACHE_FILE, cache_data)

        logger.info(f"Found {len(contracts)} OKX perpetual swap contracts")
        return contracts

    except Exception as e:
        logger.error(f"Failed to fetch OKX contracts: {e}")
        # Return cached data if available, even if expired
        if cached:
            contracts = cached.get('contracts', [])
            logger.warning("Using expired cached data due to API failure")
            return contracts
        return []

def filter_top_swap_symbols(marketcap_symbols: List[str], okx_contracts: List[str]) -> List[str]:
    """
    Filter market cap ranked symbols to only include those available on OKX.

    Args:
        marketcap_symbols: List of symbols from market cap ranking like ['BTC', 'ETH', ...]
        okx_contracts: List of OKX contract names like ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', ...]

    Returns:
        List of CCXT compatible symbols in market cap order like ['BTC/USDT', 'ETH/USDT', ...]
    """
    # Extract base symbols from OKX contracts (remove -USDT-SWAP suffix)
    okx_base_symbols = set()
    for contract in okx_contracts:
        if contract.endswith('-USDT-SWAP'):
            base = contract[:-10]  # Remove '-USDT-SWAP'
            okx_base_symbols.add(base.upper())

    # Filter and maintain order, return in CCXT format
    filtered_symbols = []
    for symbol in marketcap_symbols:
        if symbol in okx_base_symbols:
            ccxt_symbol = f"{symbol}/USDT"
            filtered_symbols.append(ccxt_symbol)

    logger.info(f"Filtered to {len(filtered_symbols)} tradable symbols from {len(marketcap_symbols)} market cap symbols")
    return filtered_symbols

def get_top50_by_marketcap() -> List[str]:
    """
    Get top 50 cryptocurrencies by market cap, filtered for OKX availability.

    Returns:
        List of CCXT compatible symbols like ['BTC/USDT', 'ETH/USDT', ...]
    """
    # Get market cap ranking
    marketcap_symbols = get_marketcap_top50(50)
    if not marketcap_symbols:
        logger.error("Failed to get market cap data")
        return []

    # Get OKX contracts
    okx_contracts = get_okx_swap_symbols()
    if not okx_contracts:
        logger.warning("Failed to get OKX contracts, returning market cap symbols without filtering")
        # Convert to CCXT format as fallback
        return [f"{symbol}/USDT" for symbol in marketcap_symbols]

    # Filter and return
    filtered_symbols = filter_top_swap_symbols(marketcap_symbols, okx_contracts)
    return filtered_symbols


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

def save_instruments_metadata(metadata: Dict[str, Dict[str, Any]], path: str = INSTRUMENTS_PATH):
    """
    Save instruments metadata to JSON file.

    Args:
        metadata: Dictionary mapping symbol to metadata dict
        path: File path to save to
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Prepare data for JSON
    data = {
        "symbols": [
            {
                "symbol": symbol,
                **meta,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            for symbol, meta in metadata.items()
        ],
        "count": len(metadata)
    }

    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info(f"Saved instruments metadata for {len(metadata)} symbols to {path}")
    except Exception as e:
        logger.error(f"Failed to save instruments metadata to {path}: {e}")

if __name__ == '__main__':
    logger.info("Starting top 50 symbol selection")
    
    # Activate qlib environment reminder
    print("Reminder: Ensure 'conda activate qlib' before running")
    
    symbols = get_top50_by_marketcap()
    if symbols:
        save_symbols(symbols)
        # Also save instruments metadata to a separate file
        # Create dummy metadata for compatibility
        metadata = {sym: {'market_cap_rank': i+1} for i, sym in enumerate(symbols)}
        save_instruments_metadata(metadata)
        print(f"Successfully updated top 50 symbols: {symbols[:5]}...")
    else:
        print("Failed to fetch symbols")
        exit(1)
