# Research Findings: Crypto Workflow Implementation

**Feature**: 0002-crypto-workflow
**Date**: 2025-11-08
**Researcher**: AI Assistant

## Research Tasks Completed

### 1. Crypto Data Integration
**Task**: Research how to load data/qlib_data/crypto into qlib format

**Decision**: Use existing qlib data loading mechanisms with crypto data path
**Rationale**: qlib already supports custom data providers, and data/qlib_data/crypto contains converted OHLCV data from CSV sources
**Alternatives considered**:
- Custom data loader: Rejected due to qlib's existing flexibility and to avoid duplicating functionality
- Direct CSV loading: Rejected as qlib's binary format provides better performance

**Implementation Notes**: Configure qlib.init() with crypto data path, reuse existing DataHandler classes

### 2. Backtest Configuration
**Task**: Research crypto-specific trading parameters (0.1% fees, 24/7 trading)

**Decision**: Configure backtest with 0.1% maker/taker fees and 24/7 trading schedule
**Rationale**: Matches OKX exchange fee structure and crypto market characteristics (no weekend closures)
**Alternatives considered**:
- Stock-based fees (0.05% open, 0.15% close): Rejected due to crypto market differences
- Zero fees: Rejected as unrealistic for production backtesting

**Implementation Notes**: Update exchange_kwargs in port_analysis_config with crypto-appropriate parameters

### 3. Time Frequency Handling
**Task**: Research 15-minute data processing in qlib

**Decision**: Use 15-minute frequency for higher resolution crypto analysis
**Rationale**: Provides better granularity than daily data for crypto trading signals and matches user specification
**Alternatives considered**:
- Daily frequency: Rejected due to insufficient resolution for crypto markets
- Hourly frequency: Considered but 15-min provides better signal timing

**Implementation Notes**: Set time_per_step to "15min" in executor configuration

### 4. Instrument Universe
**Task**: Research top 50 symbols configuration from config/top50_symbols.json

- **Decision**: Extend config_manager.py with workflow-specific methods
- **Rationale**: Existing module provides robust parameter management, can be extended with typed accessors
- **Alternatives considered**: Inline configuration (rejected due to maintainability and reusability)

**Implementation Notes**: Read symbols from config file and filter qlib instruments accordingly

## Technical Feasibility Assessment

### Data Availability
- ✅ Confirmed: data/qlib_data/crypto contains OHLCV data converted from CSV
- ✅ Compatible: qlib can load this format with proper provider configuration

### Framework Compatibility
- ✅ Confirmed: qlib workflow_by_code.py structure can be adapted for crypto
- ✅ Compatible: Existing model, dataset, and analysis components work with crypto data

### Performance Expectations
- ✅ Feasible: 15-minute data processing should complete within 30-minute target
- ✅ Scalable: Top 50 instruments manageable with existing infrastructure

## Open Questions Resolved
- All NEEDS CLARIFICATION items from technical context have been addressed
- No blocking technical unknowns remain
- Implementation can proceed with confidence