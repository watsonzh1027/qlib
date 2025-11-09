# Implementation Plan: 0002-crypto-workflow

**Branch**: `0002-crypto-workflow` | **Date**: 2025-11-08 | **Spec**: /specs/0002-crypto-workflow/spec.md
**Input**: Feature specification from `/specs/0002-crypto-workflow/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a complete crypto trading workflow based on the existing workflow_by_code.py framework, adapted for crypto data from OKX with 15-minute frequency, top 50 instruments, and crypto-specific trading parameters.

## Technical Context

**Language/Version**: Python 3.x (qlib compatible)  
**Primary Dependencies**: qlib, pandas, numpy, scikit-learn, scripts/config_manager.py  
**Storage**: data/qlib_data/crypto (OHLCV data converted from CSV)  
**Testing**: pytest  
**Target Platform**: Linux  
**Project Type**: single (Python script/library)  
**Performance Goals**: Complete workflow in under 30 minutes for typical dataset  
**Constraints**: Must reuse existing qlib framework structure, adapt for crypto data, use config_manager.py for parameter management  
**Scale/Scope**: Top 50 crypto instruments, 15-minute frequency, 2021-2024 time period  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- TDD Compliance: All new features must follow Red-Green-Refactor cycle with unit and integration tests.
- Test Coverage: Ensure project maintains >=70% overall test coverage.
- Spec-Driven Development: Feature must align with SDD principles for quality and completeness.

## Project Structure

### Documentation (this feature)

```text
specs/0002-crypto-workflow/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
examples/
├── workflow_crypto.py   # New crypto workflow script using config_manager.py

scripts/
├── config_manager.py    # Existing parameter management module (modified for crypto workflow)

qlib/
├── [existing structure] # Reuse existing qlib components

tests/
├── test_workflow_crypto.py  # Unit and integration tests for crypto workflow
```

**Structure Decision**: Single project structure using existing qlib framework and config_manager.py. New workflow script in examples/, config_manager.py extended for workflow parameters.

## Complexity Tracking

| Component | Complexity | Rationale |
|-----------|------------|-----------|
| Data Loading | Medium | Adapt qlib data handlers for crypto OHLCV format |
| Model Training | Low | Reuse existing GBDT model configuration |
| Signal Generation | Low | Reuse existing signal record logic |
| Backtesting | Medium | Adapt executor and strategy for crypto parameters |
| Analysis | Low | Reuse existing analysis record logic |

## Phase 0: Outline & Research

### Research Tasks

1. **Crypto Data Integration**: Research how to load data/qlib_data/crypto into qlib format
2. **Backtest Configuration**: Research crypto-specific trading parameters (0.1% fees, 24/7 trading)
3. **Time Frequency Handling**: Research 15-minute data processing in qlib
4. **Instrument Universe**: Research top 50 symbols configuration from config/top50_symbols.json
5. **Parameter Management**: Research extending config_manager.py for workflow parameters

### Research Findings

- **Decision**: Use existing qlib data loading mechanisms with crypto data path
- **Rationale**: qlib already supports custom data providers, data/qlib_data/crypto contains converted OHLCV data
- **Alternatives considered**: Custom data loader (rejected due to qlib's flexibility)

- **Decision**: Configure backtest with crypto fees (0.1% maker/taker) and 24/7 trading
- **Rationale**: Matches OKX fee structure and crypto market characteristics
- **Alternatives considered**: Stock-based fees (rejected due to crypto market differences)

- **Decision**: Use 15-minute frequency for higher resolution crypto analysis
- **Rationale**: Provides better granularity than daily data for crypto trading signals
- **Alternatives considered**: Daily frequency (rejected due to insufficient resolution)

- **Decision**: Load top 50 instruments from config/top50_symbols.json
- **Rationale**: Pre-defined universe ensures consistency and covers major crypto assets
- **Alternatives considered**: All available instruments (rejected due to scope complexity)

- **Decision**: Extend config_manager.py for workflow parameters
- **Rationale**: Existing module provides centralized parameter management, can be adapted for workflow config
- **Alternatives considered**: Inline configuration (rejected due to maintainability)

## Phase 1: Design & Contracts

### Data Model

**Crypto Instrument Entity**:
- Fields: symbol (string), base_currency (string), quote_currency (string)
- Relationships: None (standalone entities)
- Validation: Symbol must be in top 50 list

**OHLCV Data Entity**:
- Fields: timestamp (datetime), open (float), high (float), low (float), close (float), volume (float)
- Relationships: Belongs to Crypto Instrument
- Validation: OHLCV values must be positive, timestamp within 2021-2024 range

**Trading Signal Entity**:
- Fields: instrument (string), timestamp (datetime), signal (float), confidence (float)
- Relationships: References Crypto Instrument
- Validation: Signal in [-1, 1] range

**Backtest Result Entity**:
- Fields: portfolio_value (float), returns (float), sharpe_ratio (float), max_drawdown (float)
- Relationships: Aggregates Trading Signals
- Validation: Financial metrics must be calculable

### API Contracts

Since this is a Python script workflow, no external APIs are defined. Internal contracts:

- ConfigManager.get_workflow_config() → Dict (workflow parameters)
- ConfigManager.get_model_config() → Dict (model parameters)  
- ConfigManager.get_trading_config() → Dict (trading parameters)
- DataLoader.load_crypto_data() → DataFrame
- ModelTrainer.train() → TrainedModel
- SignalGenerator.generate() → SignalDataFrame
- BacktestExecutor.run() → BacktestResults

### Quickstart

1. Ensure data/qlib_data/crypto contains OHLCV data
2. Run `python examples/workflow_crypto.py`
3. View results in experiment recorder

## Constitution Compliance

- **TDD**: Will implement tests for each component (data loading, training, backtesting)
- **Test Coverage**: New code will maintain >=70% coverage
- **SDD**: Plan follows spec requirements exactly

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data format incompatibility | High | Validate data loading with sample data first |
| Performance degradation | Medium | Profile and optimize data processing steps |
| Model convergence issues | Medium | Add fallback model configurations |
| Configuration errors | Medium | Use config_manager.py validation and defaults |

## Success Metrics

- Workflow completes in <30 minutes
- All components produce valid outputs
- Backtest results show reasonable performance metrics
- Test coverage maintained >=70%