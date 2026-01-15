from typing import List, Tuple
import os


def normalize_symbol(sym: str) -> str:
    """Normalize symbol to form BASE_QUOTE (Internal) or BASE/QUOTE (CCXT).
    We use BASE_QUOTE for filenames to avoid issues with slashes in some contexts,
    but BASE/QUOTE is standard in Qlib instruments if we want subfolders.
    """
    if sym is None:
        return sym

    s = str(sym).strip().upper()
    # If it's already a full hierarchical symbol (BASE_QUOTE/interval/market), preserve it
    if s.count('/') == 2:
        return s

    # Replace common separators with underscores for internal consistency
    s = s.replace('-', '_').replace('/', '_').replace(' ', '_')
    
    # If it's already normalized with underscore, return it
    if '_' in s:
        return s
        
    # Known quote symbols by preference of length
    known_quotes = ['USDT', 'USDC', 'BUSD', 'USD', 'BTC', 'ETH', 'BNB']
    for q in known_quotes:
        if s.endswith(q) and len(s) > len(q):
            base = s[:-len(q)]
            return f"{base}_{q}"
    # Fallback: return as-is
    return s


def get_ccxt_symbol(sym: str) -> str:
    """Convert internal BASE_QUOTE to CCXT BASE/QUOTE.
    Also handles hierarchical Qlib symbols by taking the first part.
    """
    if not sym:
        return sym
    
    parts = sym.split('/')
    base_part = parts[0]
    ccxt_base = base_part.replace('_', '/')
    
    # If it's a future/swap and specifically for OKX (heuristically), 
    # we often need :USDT suffix for linear perpetuals.
    if len(parts) == 3 and parts[2].upper() in ['FUTURE', 'SWAP']:
        if '/USDT' in ccxt_base and ':' not in ccxt_base:
            return f"{ccxt_base}:USDT"
            
    return ccxt_base


def normalize_symbols_list(symbols: List[str]) -> List[str]:
    """Normalize a list of symbols; skip None/invalid entries."""
    normalized = []
    if not symbols:
        return []
    for sym in symbols:
        if not sym:
            continue
        try:
            normalized.append(normalize_symbol(sym))
        except Exception:
            # Skip any symbol that errors out during normalization
            continue
    return normalized


def get_data_path(root: str, symbol: str, interval: str, market_type: str, ext: str = "csv") -> str:
    """
    Generate hierarchical path for data.
    Example: data/raw/crypto/ETH_USDT/4h/future/ETH_USDT.csv
    """
    sym = normalize_symbol(symbol)
    return os.path.join(root, sym, interval, market_type, f"{sym}.{ext}")


def get_qlib_symbol(symbol: str, interval: str, market_type: str) -> str:
    """
    Generate Qlib-compatible symbol representing hierarchical path.
    Example: ETH_USDT/4h/future
    """
    sym = normalize_symbol(symbol)
    return f"{sym}/{interval}/{market_type}"


def parse_qlib_symbol(qlib_symbol: str) -> Tuple[str, str, str]:
    """
    Parse hierarchical symbol back into components.
    Example: ETH_USDT/4h/future -> (ETH_USDT, 4h, future)
    """
    parts = qlib_symbol.split('/')
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    # Fallback for legacy
    return qlib_symbol, "", ""
