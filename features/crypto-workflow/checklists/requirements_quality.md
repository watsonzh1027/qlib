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
- [ ] CHK001 - Are data source integration requirements explicitly listed with required endpoints and frequency (e.g., ccxt.fetch_ohlcv for OKX) ? [Completeness, Spec §Data Collection & Processing]
- [ ] CHK002 - Are the supported time granularities (1m/5m/15min/1h/1d) specified and prioritized for MVP (15min included per Q1)? [Completeness, Spec §Assumptions]
- [ ] CHK003 - Are storage and file layout requirements documented (folder conventions, Parquet vs CSV, manifest schema)? [Completeness, Spec §Data Collection & Processing]
- [ ] CHK004 - Are mandatory metadata fields for collected files (exchange, symbol, interval, start/end, fetch_ts) defined? [Completeness, Spec §Data Collection & Processing]

### Requirement Clarity
- [ ] CHK005 - Is "data validity" quantified (acceptable % of missing rows, allowed gaps, imputation policy) ? [Clarity, Spec §Data Quality & Integrity]
- [ ] CHK006 - Is the model persistence format/contract specified (file format, model_version, path convention) or explicitly left as implementation detail? [Clarity, Spec §Model Training & Evaluation]
- [ ] CHK007 - Are signal definitions (BUY/SELL/HOLD) defined with precise thresholds or left as ambiguous "model output mapping"? [Clarity, Spec §Trading Signal Reliability]
- [ ] CHK008 - Are backtest assumptions (order execution timing, market order fill policy) expressed precisely (e.g., "assume fill at next candle open")? [Clarity, Spec §Model Evaluation Standards]

### Requirement Consistency
- [ ] CHK009 - Do requirements for data intervals, storage retention and processing windows align between Data Collection, Feature Generation and Backtest sections ? [Consistency, Spec §Data Collection & Processing / §Signal Generation & Backtesting]
- [ ] CHK010 - Are naming conventions for symbols and intervals consistent across spec, data-model.md and quickstart.md? [Consistency, /home/watson/work/qlib/features/crypto-workflow/data-model.md and quickstart.md]
- [ ] CHK011 - Are model evaluation metrics referenced consistently (which metrics are required for acceptance: accuracy, Sharpe, max_drawdown)? [Consistency, Spec §Model Evaluation Standards]

### Acceptance Criteria Quality (Measurability)
- [ ] CHK012 - Are success criteria measurable and unambiguous (e.g., "Data preprocessing completes with 99.9% validity" rather than "data is clean")? [Measurability, Spec §Success Criteria]
- [ ] CHK013 - Are model performance acceptance thresholds (e.g., minimum accuracy or percentage of profitable periods) specified and assigned to release gates? [Measurability, Spec §Success Criteria]
- [ ] CHK014 - Are backtest performance metrics defined with calculation methods (Sharpe: annualized with risk-free 0%, drawdown definition)? [Measurability, Spec §Signal Generation & Backtesting]

### Scenario Coverage
- [ ] CHK015 - Are primary, alternate, exception and recovery scenarios enumerated for data collection (e.g., API downtime, partial data, rate-limit errors)? [Coverage, Spec §Data Quality & Integrity]
- [ ] CHK016 - Are model training failure modes and retraining triggers defined (e.g., data drift threshold, periodic retrain cadence)? [Coverage, Spec §Model Evaluation Standards]
- [ ] CHK017 - Are edge-case trading scenarios specified (asset halts, extreme volatility, zero-volume windows)? [Coverage, Spec §Trading Signal Reliability]

### Edge Case Coverage
- [ ] CHK018 - Is the behavior for missing historical data defined for backtests (skip, impute, abort)? [Edge Case, Spec §Backtest]
- [ ] CHK019 - Is the handling of symbols that change naming or delisted on exchange specified? [Edge Case, Spec §Data Collection & Processing]
- [ ] CHK020 - Are acceptable bounds for outlier prices/volumes and the filter policy defined? [Edge Case, Spec §Data Quality & Integrity]

### Non-Functional Requirements
- [ ] CHK021 - Are performance expectations for pipeline stages (e.g., time to preprocess 1 year of 1m data, or training wall-time targets) specified or intentionally excluded? [NFR, Spec §Performance Requirements]
- [ ] CHK022 - Are resource and storage sizing assumptions documented (disk, memory) for expected dataset sizes? [NFR, Spec §Assumptions]
- [ ] CHK023 - Is availability/latency requirement for near-real-time prediction defined (if real-time use-case in scope)? [NFR, Spec §Core Principles]

### Dependencies & Assumptions
- [ ] CHK024 - Are external dependencies (ccxt, OKX API quotas, LightGBM availability) listed with their assumed versions and constraints? [Dependencies, research.md]
- [ ] CHK025 - Are configuration defaults and override mechanisms defined (fees, slippage, model_version mapping)? [Assumption, quickstart.md / config_defaults.md]

### Ambiguities & Conflicts (what to clarify)
- [ ] CHK026 - Is it explicit whether the spec requires multi-exchange parity at MVP or only design-for-others? (RESOLVED: Q2 = OKX-only → update spec to mark multi-exchange as out-of-scope for MVP) [Ambiguity, Spec §Data Collection & Processing]
- [ ] CHK027 - Is the required test strategy (TDD) spelled out for each component (unit, integration, backtest smoke) and tied to CI gating? [Ambiguity, constitution.md / tasks.md]
- [ ] CHK028 - Are versioning and traceability requirements for data & models specified (manifest schema, model id & provenance)? [Ambiguity, data-model.md]

### Traceability & Documentation
- [ ] CHK029 - Is a requirement ID scheme defined and used consistently in spec and tasks.md for traceability? [Traceability, Spec §Governance]
- [ ] CHK030 - Do ≥80% of checklist items reference a spec section or artifact (spec.md, data-model.md, research.md) as required by traceability rules? [Traceability]

## Notes / Next steps
- User selections applied: Q1 = include 15min granularity; Q2 = OKX-only for MVP; Q3 = fixed percent fee + fixed slippage.  
- Update spec, data-model.md, quickstart.md and tasks.md to reflect these choices and remove [Gap]/[Ambiguity] markers for resolved items (notably CHK002 and CHK026).  
- Prioritize resolving CHK005, CHK007, CHK008, CHK015 as blockers before implementation.  
- This run created requirements_quality.md (subsequent runs will create new files rather than overwriting).

