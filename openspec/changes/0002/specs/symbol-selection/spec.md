# Specification: Symbol Selection (change 0002)

## Why
The current symbol selection methodology in `scripts/get_top50.py` incorrectly ranks cryptocurrencies by funding rate instead of market capitalization. This change corrects the selection criteria to:

- Use market capitalization as the primary ranking metric for identifying significant cryptocurrencies
- Filter selected symbols for actual tradability on OKX exchange perpetual contracts
- Ensure output format compatibility with OKX's contract naming conventions
- Provide accurate symbol selection for quantitative trading strategies

## ADDED Requirements

### Requirement: Market Cap Based Ranking
- The system MUST fetch cryptocurrency market capitalization data from CoinGecko API.
- The system MUST rank the top 50 coins by market cap descending.
- The system MUST return a list of uppercase symbol strings.

#### Scenario: Successful API Call
**Given** CoinGecko API is available and responding  
**When** `get_marketcap_top50()` is called with `top_n=50`  
**Then** returns a list of 50 uppercase symbol strings  
**And** symbols are ordered by market cap descending  
**And** first symbol is "BTC" (Bitcoin)

#### Scenario: API Failure with Cached Data
**Given** CoinGecko API is unavailable  
**And** cached market cap data exists from previous successful call  
**Then** returns cached data with warning logged  
**And** cache timestamp is within 1 hour

#### Scenario: Complete API Failure
**Given** CoinGecko API is unavailable  
**And** no cached data exists  
**Then** returns empty list  
**And** logs error message  
**And** does not crash the application

### Requirement: OKX Contract Discovery
- The system MUST discover all available OKX perpetual swap contracts.
- The system MUST filter contracts for USDT-based perpetual swaps.
- The system MUST return contract names ending with "-USDT-SWAP".

#### Scenario: Successful Contract Discovery
**Given** OKX exchange API is available  
**When** `get_okx_swap_symbols()` is called  
**Then** returns list of strings ending with "-USDT-SWAP"  
**And** all returned contracts are actively tradable  
**And** list contains major coins like "BTC-USDT-SWAP"

#### Scenario: Exchange API Failure
**Given** OKX API is temporarily unavailable  
**Then** returns empty list  
**And** logs warning about API unavailability  
**And** does not block market cap data fetching

### Requirement: Symbol Filtering and Matching
- The system MUST combine market cap ranking with OKX contract availability.
- The system MUST match symbol base names with available contracts.
- The system MUST return final list in CCXT compatible format "BASE/USDT".

#### Scenario: Perfect Intersection Match
**Given** top 50 market cap coins: ["BTC", "ETH", "SOL", ...]  
**And** OKX contracts: ["BTC-USDT-SWAP", "ETH-USDT-SWAP", ...]  
**When** `filter_top_swap_symbols()` is called  
**Then** returns ["BTC/USDT", "ETH/USDT", ...]  
**And** maintains market cap ranking order  
**And** excludes coins without OKX contracts

#### Scenario: Partial Match with Gaps
**Given** some top market cap coins have no OKX contracts  
**When** filtering is applied  
**Then** returns only coins with available contracts  
**And** maintains relative ranking of available coins  
**And** result count is less than 50

#### Scenario: Symbol Format Handling
**Given** market cap symbols may have case variations  
**And** contract names use specific formatting  
**When** matching occurs  
**Then** handles case-insensitive matching  
**And** properly extracts base symbol from contract names  
**And** returns standardized "SYMBOL/USDT" format

### Requirement: Data Persistence and Caching
- The system MUST cache API results to reduce external dependencies.
- The system MUST implement appropriate cache expiration times.
- The system MUST store cache in human-readable JSON format.

#### Scenario: Market Cap Data Caching
**Given** successful CoinGecko API call  
**When** data is fetched  
**Then** caches result locally with timestamp  
**And** subsequent calls within 1 hour return cached data  
**And** cache file is human-readable JSON format

#### Scenario: Contract Data Caching
**Given** successful OKX contract discovery  
**When** data is fetched  
**Then** caches contract list for 15 minutes  
**And** uses cached data for subsequent calls  
**And** automatically refreshes expired cache

### Requirement: Error Handling and Resilience
- The system MUST handle various failure scenarios gracefully.
- The system MUST implement appropriate retry and backoff strategies.
- The system MUST log detailed error information for debugging.

#### Scenario: Network Timeout
**Given** API call takes longer than timeout threshold  
**Then** aborts the call  
**And** returns cached data if available  
**And** logs timeout warning

#### Scenario: Malformed API Response
**Given** API returns invalid JSON or unexpected structure  
**Then** logs detailed error information  
**And** returns empty result or cached data  
**And** does not attempt to process corrupted data

#### Scenario: Rate Limit Exceeded
**Given** API rate limit is reached  
**Then** implements exponential backoff  
**And** retries after appropriate delay  
**And** logs rate limit events for monitoring  

### Requirement: Configuration Integration
- The symbol selection MUST integrate with the centralized configuration system.
- The system MUST read configuration parameters from workflow.json.
- The system MUST support environment-specific configuration.

#### Scenario: Configurable API Endpoints
**Given** workflow.json contains API configuration  
**Then** uses configured endpoints instead of hardcoded URLs  
**And** supports environment-specific API settings  

#### Scenario: Configurable Parameters
**Given** workflow.json contains selection parameters  
**Then** uses configured top_n value (default 50)  
**And** uses configured cache timeouts  
**And** supports disabling caching for testing  

## MODIFIED Requirements

None - this change introduces new functionality rather than modifying existing requirements.  

## REMOVED Requirements

None - this change replaces incorrect behavior rather than removing existing requirements.  

## Cross-References

### Related Capabilities
- **Data Collection**: Uses symbol list for targeted data fetching
- **Data Conversion**: Depends on correct symbol format for Qlib compatibility
- **Backtesting**: Requires accurate symbol selection for valid results

### Implementation Dependencies
- **CoinGecko API**: External dependency for market cap data
- **CCXT Library**: Required for OKX exchange integration
- **Configuration System**: Depends on workflow.json for settings

## Testing Requirements

### Unit Test Coverage
- [ ] All API interaction functions mocked
- [ ] Error conditions tested with various failure modes
- [ ] Caching behavior validated
- [ ] Symbol format transformations tested

### Integration Test Coverage
- [ ] End-to-end symbol selection pipeline
- [ ] Real API calls with proper rate limiting
- [ ] Configuration loading and parameter handling
- [ ] Cache persistence and expiration

### Performance Benchmarks
- [ ] API call latency under 5 seconds
- [ ] Memory usage under 100MB
- [ ] Cache hit ratio above 80%
- [ ] Error recovery within 10 seconds