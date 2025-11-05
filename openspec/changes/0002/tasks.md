# Tasks for Change 0002: Fix Top 50 Crypto Selection Method

## Overview
This change fixes the incorrect symbol selection methodology in `scripts/get_top50.py` by implementing market cap-based ranking filtered for OKX perpetual contract availability.

## Task Breakdown

### Phase 1: Core Implementation

#### 1.1 Implement Market Cap Fetching
- [ ] Create `get_marketcap_top50()` function using CoinGecko API
- [ ] Add proper error handling for API failures
- [ ] Return list of uppercase symbols (e.g., ["BTC", "ETH", ...])
- [ ] Add unit tests for API response parsing

#### 1.2 Implement OKX Contract Discovery
- [ ] Create `get_okx_swap_symbols()` function using CCXT
- [ ] Filter for contracts ending with "-USDT-SWAP"
- [ ] Add caching to avoid repeated API calls
- [ ] Add unit tests for contract filtering

#### 1.3 Implement Symbol Filtering Logic
- [ ] Create `filter_top_swap_symbols()` function
- [ ] Match market cap symbols with OKX contract availability
- [ ] Return final list in OKX perpetual contract format
- [ ] Add validation for symbol format consistency

### Phase 2: Integration and Testing

#### 2.1 Update Main Function
- [ ] Replace `get_okx_funding_top50()` with new filtering logic
- [ ] Update output format to use OKX contract names
- [ ] Maintain backward compatibility for existing callers
- [ ] Add logging for symbol selection process

#### 2.2 Configuration Updates
- [ ] Update `workflow.json` to reflect new methodology
- [ ] Add configuration options for API endpoints and caching
- [ ] Update documentation for new symbol selection approach

#### 2.3 Comprehensive Testing
- [ ] Add unit tests for each component function
- [ ] Add integration tests for end-to-end pipeline
- [ ] Test with mocked APIs for deterministic results
- [ ] Validate against known good symbol lists

### Phase 3: Validation and Deployment

#### 3.1 Data Validation
- [ ] Run against live APIs to verify symbol accuracy
- [ ] Compare output with expected top market cap coins
- [ ] Validate that all returned symbols are OKX-tradable
- [ ] Check for duplicates or invalid symbols

#### 3.2 Downstream Compatibility
- [ ] Update `okx_data_collector.py` to handle new symbol format
- [ ] Update `convert_to_qlib.py` for contract name changes
- [ ] Test data collection pipeline with new symbols
- [ ] Verify backtesting works with updated symbol list

#### 3.3 Documentation and Monitoring
- [ ] Update README with new symbol selection methodology
- [ ] Add monitoring for API health and symbol changes
- [ ] Document troubleshooting steps for API failures
- [ ] Create runbook for manual symbol list updates

## Dependencies

### Parallel Work
- None identified - this is a self-contained change

### Sequential Dependencies
1. **Task 1.1** must complete before **Task 1.3**
2. **Task 1.2** must complete before **Task 1.3**
3. **Task 2.1** requires **Tasks 1.1-1.3** completion
4. **Task 2.3** requires **Task 2.1** completion
5. **Tasks 3.1-3.2** require **Task 2.1** completion

## Validation Criteria

### Functional Validation
- [ ] Output contains exactly the intersection of top 50 market cap coins and OKX perpetual contracts
- [ ] All returned symbols are in format "SYMBOL-USDT-SWAP"
- [ ] No duplicate symbols in output
- [ ] Symbol count is reasonable (expected: 30-45 symbols)

### Performance Validation
- [ ] CoinGecko API calls complete within 5 seconds
- [ ] OKX API calls complete within 2 seconds
- [ ] Total execution time under 10 seconds
- [ ] Memory usage remains under 100MB

### Reliability Validation
- [ ] Graceful handling of API failures (returns cached/empty results)
- [ ] Proper error logging for debugging
- [ ] No crashes on network timeouts
- [ ] Idempotent execution (multiple runs produce same results)

## Rollback Plan

### Quick Rollback
1. Revert `scripts/get_top50.py` to previous version
2. Restore backup of `config/top50_symbols.json`
3. Restart data collection services

### Gradual Rollback
1. Add feature flag to switch between old/new methods
2. Monitor for issues with new implementation
3. Switch back to old method if problems detected
4. Remove feature flag after successful validation

## Success Metrics

### Quantitative Metrics
- Symbol accuracy: >95% match with expected top market cap coins
- Contract availability: 100% of returned symbols tradable on OKX
- API success rate: >99% successful API calls
- Execution time: <10 seconds average

### Qualitative Metrics
- Code readability: Clear function separation and documentation
- Error handling: Comprehensive error coverage
- Test coverage: >90% code coverage
- Documentation: Complete API documentation and examples