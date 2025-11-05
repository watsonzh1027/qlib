# Design: Fix Top 50 Crypto Selection Method (change 0002)

## Overview

This change addresses the incorrect symbol selection methodology in `scripts/get_top50.py`. The current implementation ranks cryptocurrencies by funding rate, which is not the intended behavior for selecting the most significant market participants.

## Architectural Considerations

### Current Architecture Issues

1. **Incorrect Ranking Criteria**: Using funding rates instead of market cap leads to selection bias toward leveraged trading instruments rather than market significance.

2. **Missing Availability Filtering**: No validation that selected symbols are actually tradable on the target exchange.

3. **Format Inconsistency**: Output format doesn't match exchange's contract naming conventions.

### Proposed Architecture

```
CoinGecko API → Market Cap Ranking → OKX Contract Filter → Tradable Symbols
      ↓              ↓                      ↓              ↓
   Raw Data    Top 50 by Market Cap    Available Contracts    BTC-USDT-SWAP
```

### Component Design

#### 1. Market Data Provider (`get_marketcap_top50()`)
- **API**: CoinGecko `/coins/markets` endpoint
- **Parameters**: 
  - `vs_currency`: "usd"
  - `order`: "market_cap_desc"
  - `per_page`: 50
- **Output**: List of uppercase symbols (e.g., ["BTC", "ETH", ...])

#### 2. Exchange Contract Provider (`get_okx_swap_symbols()`)
- **API**: CCXT OKX exchange markets
- **Filter**: Contracts ending with "-USDT-SWAP"
- **Output**: List of available perpetual contracts

#### 3. Symbol Filter (`filter_top_swap_symbols()`)
- **Input**: Market cap ranked symbols + OKX available contracts
- **Logic**: Match symbol base names (e.g., "BTC" → "BTC-USDT-SWAP")
- **Output**: Final list of tradable perpetual contracts

### Data Flow

```python
def filter_top_swap_symbols():
    # 1. Get market cap ranking
    top_symbols = get_marketcap_top50()  # ["BTC", "ETH", ...]
    
    # 2. Get available contracts  
    okx_swaps = get_okx_swap_symbols()   # ["BTC-USDT-SWAP", ...]
    
    # 3. Filter intersection
    result = []
    for symbol in top_symbols:
        for contract in okx_swaps:
            if contract.startswith(f"{symbol}-"):
                result.append(contract)
    
    return result  # ["BTC-USDT-SWAP", "ETH-USDT-SWAP", ...]
```

## Error Handling

### API Failures
- **CoinGecko API**: Return cached results if available, log warning
- **OKX API**: Return empty list, log error, don't block market cap fetching

### Data Validation
- **Empty Responses**: Log warnings, return empty lists
- **Malformed Data**: Validate JSON structure, skip invalid entries
- **Rate Limits**: Implement exponential backoff for API calls

## Performance Considerations

### Caching Strategy
- Cache CoinGecko results for 1 hour (market caps change slowly)
- Cache OKX contract list for 15 minutes (contracts change rarely)
- Store cache in local JSON files with timestamps

### Rate Limiting
- CoinGecko: 10-30 calls/minute (use delays between calls)
- OKX: 10 calls/second (minimal impact for market list)

## Testing Strategy

### Unit Tests
- Mock API responses for deterministic testing
- Test each component function independently
- Validate symbol format transformations

### Integration Tests
- Test end-to-end symbol selection pipeline
- Verify actual API connectivity (with rate limiting)
- Validate output against known good data

### Edge Cases
- Network failures during API calls
- Empty or partial API responses
- New symbols not yet in OKX listings
- Market cap ranking changes during execution

## Backward Compatibility

### Breaking Changes
- Output format changes from `["BTC/USDT", ...]` to `["BTC-USDT-SWAP", ...]`
- Configuration keys may need updates

### Migration Path
1. Deploy new implementation alongside old
2. Update downstream consumers to handle new format
3. Switch configuration to use new implementation
4. Remove old implementation after validation

## Security Considerations

### API Key Management
- No API keys required for CoinGecko (free tier)
- OKX API calls are public market data only
- No sensitive data exposure

### Data Validation
- Validate all external API responses
- Sanitize symbol names to prevent injection
- Log API errors without exposing sensitive details

## Monitoring and Observability

### Logging
- Info: Successful API calls and symbol counts
- Warning: API failures with fallback behavior
- Error: Complete failures requiring intervention

### Metrics
- API response times
- Symbol count changes
- Cache hit/miss ratios
- Error rates by component