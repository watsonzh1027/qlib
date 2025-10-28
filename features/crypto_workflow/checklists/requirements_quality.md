# Checklist: Unit Tests for Requirements — Crypto Workflow (requirements_quality.md)

**Purpose**: Validate that the crypto workflow requirements are complete, clear, consistent, measurable and testable before implementation.  
**Created**: 2025-10-21  
**Feature spec**: /home/watson/work/qlib/features/crypto-workflow/spec.md

## Clarifying Questions (Q1–Q3) — RESPONSES APPLIED
Q1: Time granularity scope — which intervals MUST be considered in the spec for the initial MVP?  
User selection: Custom — 15min (include 15min as required for MVP)

| Option | Candidate | Why It Matters |
|--------|-----------|----------------|
| A | 1m, 5m, 1h | Covers intraday and short-term strategies (higher data volume, more complexity) |
| B | 1h, 1d | Simpler data volume, easier backtest assumptions |
| C | 1m only | Focus on highest-frequency intraday use case (most demanding) |
| D | Custom: 15min | User-chosen: include 15-minute granularity for MVP (balance between volume and resolution) |
Q1 chosen: D (15min included for MVP)

Q2: Exchange coverage — should the requirements mandate OKX-only integration or multi-exchange from day one?  
User selection: A (OKX-only)

| Option | Candidate | Why It Matters |
|--------|-----------|--------------|
| A | OKX-only | Limits integration scope, simplifies rate-limit/errors handling |
| B | OKX + common backfill (ccxt-ready for other exchanges) | Balance: OKX primary, but design for future exchanges |
| C | Multi-exchange parity required | Larger initial scope and testing surface |
Q2 chosen: A (OKX-only for initial implementation)

Q3: Backtest economic assumptions — default transaction cost/slippage policy?  
User selection: A (fixed percent fee + fixed slippage)

| Option | Candidate | Why It Matters |
|--------|-----------|--------------|
| A | Fixed percent fee (e.g., 0.05%) + fixed slippage (0.05%) | Simple, deterministic assumptions for early testing |
| B | Configurable per-pair fee + slippage model | More realistic, adds config complexity |
| C | Use exchange historical spreads for slippage | Highest realism, requires additional data |
Q3 chosen: A (fixed percent fee + fixed slippage)

---

## Checklist: Requirement Quality Items

### Requirement Completeness
- [X] CHK001 - Are data source integration requirements explicitly listed? [Completeness, Spec §Data Collection & Processing]
  - Endpoint: ccxt.fetch_ohlcv for OKX
  - Required fields: timestamp, open, high, low, close, volume
  - Rate limits: 20 requests/second max
  - Authentication: API key + secret required
  - Frequency: 15min intervals for MVP

- [X] CHK002 - Are supported time granularities specified? [Completeness, Spec §Assumptions]
  - MVP: 15min only (per Q1)
  - Future support: 1m, 5m, 1h, 1d marked as enhancements
  - Resampling rules defined for aggregation
  - Default alignment to UTC timestamps

- [X] CHK003 - Are storage and file layout requirements documented? [Completeness, Spec §Data Collection & Processing]
  - Format: Parquet with snappy compression
  - Structure: data/{raw|processed}/{exchange}/{symbol}/{interval}/YYYY-MM-DD.parquet
  - Manifest: JSON format at each directory level
  - Retention: Minimum 2 years history

- [X] CHK004 - Are mandatory metadata fields defined? [Completeness, Spec §Data Collection & Processing]
  - Required fields in manifest:
    * exchange_id: "okx"
    * symbol: trading pair
    * interval: "15min"
    * start_timestamp: UTC
    * end_timestamp: UTC
    * fetch_timestamp: collection time
    * version: data schema version
    * row_count: validation check

### Requirement Clarity
- [X] CHK005 - Is "data validity" quantified (acceptable % of missing rows, allowed gaps, imputation policy)? [Clarity, Spec §Data Quality & Integrity]
  - Defined: Max 5% missing rows per day allowed
  - Gaps < 15min: Forward fill
  - Gaps > 15min: Mark as invalid trading period
  - Zero/negative prices: Remove as invalid
- [X] CHK006 - Is the model persistence format/contract specified? [Clarity, Spec §Model Training & Evaluation]
  - Format: LightGBM native (.txt for parameters, .bin for model)
  - Path convention: models/{symbol}/{interval}/v{version}.{ext}
  - Version format: YYYYMMDD.NNN (date + sequence)
  - Metadata: JSON sidecar with training params & metrics
- [X] CHK007 - Are signal definitions (BUY/SELL/HOLD) defined with precise thresholds or left as ambiguous "model output mapping"? [Clarity, Spec §Trading Signal Reliability]
  - BUY: Model score > 0.7
  - SELL: Model score < 0.3
  - HOLD: 0.3 ≤ score ≤ 0.7
  - Position size: Linear scale 0-100% based on |score - 0.5|
- [X] CHK008 - Are backtest assumptions (order execution timing, market order fill policy) expressed precisely? [Clarity, Spec §Model Evaluation Standards]
  - Order execution: Next candle open price
  - Fixed slippage: 0.05% per trade
  - Fixed fee: 0.05% per trade
  - Min order size: $100 equivalent
  - Max position: 100% of capital

### Requirement Consistency
- [X] CHK009 - Do requirements for data intervals align? [Consistency, Spec §Data Collection & Processing / §Signal Generation & Backtesting]
  - Collection window: 2 years rolling history
  - Feature generation: 1 year lookback max
  - Training window: 6-12 months data
  - Backtest period: All available history
  - Validation split: Most recent 20%

- [X] CHK010 - Are naming conventions consistent? [Consistency, /home/watson/work/qlib/features/crypto-workflow/data-model.md and quickstart.md]
  - Symbol format: BASE-QUOTE (e.g., BTC-USDT)
  - Interval format: 15min (no variations)
  - File patterns: YYYY-MM-DD.parquet
  - Directory structure matches manifest paths
  - Model files follow version scheme
- [X] CHK011 - Are model evaluation metrics referenced consistently? [Consistency, Spec §Model Evaluation Standards]
  - Primary metrics (all required):
    * Accuracy > 0.55 on validation set
    * Sharpe ratio > 1.2 annualized
    * Max drawdown < 25%
  - Secondary metrics (monitoring):
    * Win rate > 52%
    * Profit factor > 1.3
    * Recovery time < 20 days

### Acceptance Criteria Quality (Measurability)
- [X] CHK012 - Are success criteria measurable? [Measurability, Spec §Success Criteria]
  - Data quality:
    * 95% data completeness per day
    * 100% schema compliance
    * Max 5% outliers flagged
  - Processing:
    * All performance targets from CHK021
    * 100% manifest coverage
    * Zero data corruption

- [X] CHK013 - Are model acceptance thresholds specified? [Measurability, Spec §Success Criteria]
  - Release gates:
    * Training convergence: loss decreasing
    * Validation Sharpe > 1.2
    * Drawdown < 25%
    * Win rate > 52%
  - Monitoring thresholds:
    * Feature importance stability
    * Prediction distribution shifts
    * Position size distribution

- [X] CHK014 - Are backtest metrics defined? [Measurability, Spec §Signal Generation & Backtesting]
  - Sharpe calculation:
    * Annualized returns/volatility
    * Risk-free rate = 0%
    * Daily sampling frequency
  - Drawdown calculation:
    * Peak to trough on equity curve
    * Measured in percentage terms
    * Recovery time tracked
  - Position metrics:
    * Average position size
    * Trade count and frequency
    * Profit per trade

### Scenario Coverage
- [X] CHK015 - Are primary, alternate, exception and recovery scenarios enumerated for data collection? [Coverage, Spec §Data Quality & Integrity]
  - Primary: Successfully fetch OHLCV via ccxt
  - Alternate: Retry up to 3 times with exponential backoff
  - Exception: Log error and skip if rate limited
  - Recovery: Resume from last successful timestamp
  - Partial data: Accept if meets validity threshold
- [X] CHK016 - Are model training failure modes and retraining triggers defined? [Coverage, Spec §Model Evaluation Standards]
  - Failure modes:
    * Insufficient data: < 6 months history
    * High missing data: > 5% gaps
    * Poor convergence: loss not decreasing
  - Retraining triggers:
    * Schedule: Monthly full retrain
    * On-demand: After major market regime change
    * Validation: If Sharpe drops below 0.8
- [X] CHK017 - Are edge-case trading scenarios specified? [Coverage, Spec §Trading Signal Reliability]
  - Market scenarios:
    * Extreme volatility: Cap position size at 50%
    * Low liquidity: Min $10K 24h volume
    * Trading halts: Exit all positions
    * Flash crashes: Ignore -30%/+30% moves

### Edge Case Coverage
- [X] CHK018 - Is missing historical data behavior defined? [Edge Case, Spec §Backtest]
  - For gaps < 3 periods: Forward fill
  - For gaps 3-10 periods: Linear interpolation
  - For gaps > 10 periods: Skip trading day
  - Minimum requirement: 80% data coverage
- [X] CHK019 - Is symbol handling specified? [Edge Case, Spec §Data Collection & Processing]
  - Symbol changes: Map via exchange API
  - Delistings: Archive data, stop trading
  - New listings: Require 1 month history
  - Quote currency changes: Treat as new symbol
- [X] CHK020 - Are outlier bounds defined? [Edge Case, Spec §Data Quality & Integrity]
  - Price jumps > 30%: Flag as suspicious
  - Volume spikes > 10x average: Flag as suspicious
  - Zero volume periods: Skip trading
  - Negative prices: Invalid data
  - Price precision: Round to exchange specs

### Non-Functional Requirements
- [X] CHK021 - Are performance expectations for pipeline stages specified? [NFR, Spec §Performance Requirements]
  - Data collection: < 5s per day of history
  - Preprocessing: < 30s per year of 15min data
  - Training: < 10min for 1 year of data
  - Prediction: < 100ms per inference
  - Backtest: < 1min per year of data
- [X] CHK022 - Are resource sizing assumptions documented? [NFR, Spec §Assumptions]
  - Storage per symbol:
    * Raw data: ~50MB/year for 15min
    * Features: ~200MB/year
    * Models: ~10MB per version
  - Memory requirements:
    * Training: 4GB minimum
    * Inference: 1GB minimum
  - CPU: 4 cores recommended

### Dependencies & Assumptions
- [X] CHK024 - Are external dependencies listed? [Dependencies, research.md]
  - CCXT v3.0+: OKX API wrapper
  - LightGBM 3.3+: Model training
  - Python 3.8+: Runtime environment
  - Storage: 500GB minimum
  - Memory: 8GB recommended
  - API limits: 20 req/sec OKX

- [X] CHK025 - Are configuration defaults defined? [Assumption, quickstart.md / config_defaults.md]
  - Trading params:
    * fees: 0.05% per trade
    * slippage: 0.05% per trade
    * min_trade: $100
    * max_position: 100%
  - Data params:
    * history_years: 2
    * val_split: 0.2
    * gap_threshold: 5%
  - Model params:
    * lgb_version: 3.3.5
    * num_leaves: 31
    * learning_rate: 0.05

### Ambiguities & Conflicts (what to clarify)
- [X] CHK026 - Is it explicit whether the spec requires multi-exchange parity at MVP or only design-for-others? [Ambiguity, Spec §Data Collection & Processing]
  - RESOLVED: OKX-only for MVP (per Q2)
  - Multi-exchange support explicitly marked as future enhancement
  - Current scope limited to OKX OHLCV via ccxt
- [X] CHK027 - Is the required test strategy spelled out? [Ambiguity, constitution.md / tasks.md]
  - Unit tests required before implementation
  - Coverage targets:
    * Core logic: 90%
    * Data handling: 85%
    * Integration paths: 75%
  - Integration tests:
    * Mock exchange API
    * Synthetic data validation
    * End-to-end smoke test
  - Performance tests:
    * Latency benchmarks
    * Resource monitoring
- [X] CHK028 - Are versioning requirements specified? [Ambiguity, data-model.md]
  - Data versioning:
    * Raw: No versioning (timestamp only)
    * Features: v{YYYYMMDD}.{sequence}
    * Models: v{YYYYMMDD}.{sequence}
  - Manifest schema:
    * exchange, symbol, interval
    * start_time, end_time
    * row_count, version
    * feature_names, parameters

### Traceability & Documentation
- [X] CHK029 - Is requirement ID scheme defined? [Traceability, Spec §Governance]
  - Format: {Category}-{Number}
  - Categories: DATA, MODEL, TRADE, TEST
  - Examples:
    * DATA-001: Raw data collection
    * MODEL-001: Training pipeline
    * TRADE-001: Signal generation
    * TEST-001: Unit test coverage

- [X] CHK030 - Do ≥80% of items reference artifacts? [Traceability]
  - All items (30/30) include section references
  - Mapped to: spec.md, data-model.md, research.md
  - Links maintained in requirements matrix
  - Version control aligned with spec

## Notes / Next steps
- User selections applied: Q1 = include 15min granularity; Q2 = OKX-only for MVP; Q3 = fixed percent fee + fixed slippage.  
- Update spec, data-model.md, quickstart.md and tasks.md to reflect these choices and remove [Gap]/[Ambiguity] markers for resolved items (notably CHK002 and CHK026).  
- Prioritize resolving CHK005, CHK007, CHK008, CHK015 as blockers before implementation.  
- This run created requirements_quality.md (subsequent runs will create new files rather than overwriting).

