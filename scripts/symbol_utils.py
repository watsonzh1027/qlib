"""
Symbol normalization utilities

This module provides helper functions to normalize symbol formats between CCXT, config
and the internal codebase.

Functions:
- normalize_symbol: normalize legacy or differently formatted inputs into canonical "BASE/QUOTE" format.
"""
from typing import List


def normalize_symbol(sym: str) -> str:
    """Normalize symbol to form BASE/QUOTE.

    Examples:
        'BTCUSDT' -> 'BTC/USDT'
        'BTC_USDT' -> 'BTC/USDT'
        'BTC-USDT' -> 'BTC/USDT'
        'BTC/USDT' -> 'BTC/USDT'
        'solusdt' -> 'SOL/USDT'

    """
    if sym is None:
        return sym

    s = str(sym).strip().upper()
    # Replace common separators
    s = s.replace('-', '/').replace('_', '/').replace(' ', '/')
    if '/' in s:
        return s
    # Known quote symbols by preference of length
    known_quotes = ['USDT', 'USDC', 'BUSD', 'USD', 'BTC', 'ETH', 'BNB']
    for q in known_quotes:
        if s.endswith(q) and len(s) > len(q):
            base = s[:-len(q)]
            return f"{base}/{q}"
    # Fallback: return as-is
    return s


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
