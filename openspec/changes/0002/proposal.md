# Change 0002: Fix Top 50 Crypto Selection Method

Status: PROPOSED  
Created: 2025-11-05  
Author: watson  

# Pointers
- Issue: ../../issues/0025-get_top50-method-is-incorrect.md
- Tasks: tasks.md
- Design: design.md
- Specs: specs/

---

## Problem Statement

The current `scripts/get_top50.py` implementation incorrectly selects the top 50 cryptocurrencies by funding rate instead of market capitalization. This leads to incorrect symbol selection for the trading bot.

## Proposed Solution

Replace the funding rate-based ranking with a market cap-based approach that:

1. Fetches top 50 cryptocurrencies by market cap from CoinGecko API
2. Filters the list to include only symbols that have OKX perpetual swap contracts
3. Returns the final list of tradable perpetual contracts

## Changes

### 1. `scripts/get_top50.py`
- Replace `get_okx_funding_top50()` with `get_marketcap_top50()`
- Add `get_okx_swap_symbols()` to fetch available OKX perpetual contracts
- Add `filter_top_swap_symbols()` to combine market cap ranking with OKX availability
- Update output format to use OKX perpetual contract format (e.g., "BTC-USDT-SWAP")

### 2. Configuration Updates
- Update `workflow.json` to reflect the new symbol selection method
- Ensure compatibility with existing data collection and conversion scripts

### 3. Testing
- Add unit tests to verify market cap ranking accuracy
- Add integration tests to verify OKX contract filtering
- Validate that output symbols are actually tradable on OKX

## Benefits

- **Accuracy**: Symbols are now selected based on actual market capitalization rather than funding rates
- **Tradability**: Only returns symbols that have active OKX perpetual contracts
- **Consistency**: Output format matches OKX's perpetual contract naming convention
- **Maintainability**: Clear separation between market data fetching and exchange filtering

## Migration Notes

- Existing `config/top50_symbols.json` files will need to be regenerated
- Downstream scripts using the symbol list should expect OKX perpetual contract format
- No breaking changes to the data collection pipeline beyond symbol format