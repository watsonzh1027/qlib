# Feature Specification: Crypto Workflow Implementation

**Feature Branch**: `0002-crypto-workflow`  
**Created**: 2025-11-08  
**Status**: Draft  
**Input**: User description: "workflow_crypto 参考 #file:workflow_by_code.py 的框架和workflow, 实现对crypto 的数据训练和回测"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Complete Crypto Trading Workflow (Priority: P1)

As a quantitative researcher, I want to execute a complete workflow that loads crypto market data, trains a machine learning model, generates trading signals, and performs backtesting to evaluate strategy performance.

**Why this priority**: This is the core functionality that enables crypto quantitative research and strategy development.

**Independent Test**: Can be fully tested by running the workflow script and verifying that all components (data loading, model training, signal generation, backtesting) complete successfully with valid outputs.

**Acceptance Scenarios**:

1. **Given** crypto market data is available, **When** I run the workflow script, **Then** the system loads data, trains a model, generates signals, and produces backtest results.
2. **Given** a trained model and dataset, **When** I generate signals, **Then** the system produces trading signals for crypto instruments.
3. **Given** trading signals and backtest configuration, **When** I run backtesting, **Then** the system generates portfolio analysis with performance metrics.

---

### User Story 2 - Adapt Existing Framework for Crypto (Priority: P2)

As a developer, I want to reuse the existing qlib framework structure from workflow_by_code.py and adapt it specifically for crypto data instead of traditional stock data.

**Why this priority**: Enables code reuse and maintains consistency with existing qlib patterns while extending to crypto markets.

**Independent Test**: Can be tested by comparing the crypto workflow structure to the original workflow and verifying crypto-specific adaptations (data sources, time frequencies, trading costs).

**Acceptance Scenarios**:

1. **Given** the original workflow_by_code.py, **When** I adapt it for crypto, **Then** the core structure (model training, signal generation, backtesting) remains the same but uses crypto data sources.
2. **Given** crypto-specific parameters (trading hours, costs, instruments), **When** I configure the backtest, **Then** the system applies appropriate crypto market assumptions.

---

### User Story 3 - Validate Crypto Model Performance (Priority: P3)

As a researcher, I want to analyze the trained model's performance on crypto data through signal analysis and backtesting metrics.

**Why this priority**: Ensures the crypto-adapted workflow produces meaningful and analyzable results for research purposes.

**Independent Test**: Can be tested by examining the generated analysis reports and backtest metrics for reasonableness in crypto context.

**Acceptance Scenarios**:

1. **Given** a trained model on crypto data, **When** I run signal analysis, **Then** the system generates analysis reports with relevant crypto market insights.
2. **Given** backtest results, **When** I review portfolio metrics, **Then** the system provides performance statistics appropriate for crypto trading strategies.

### Edge Cases

- What happens when crypto data is incomplete or has gaps?
- How does the system handle high volatility typical in crypto markets?
- What if the model fails to converge on crypto data?
- How are crypto-specific trading costs and constraints handled?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load crypto market data using qlib data handlers
- **FR-002**: System MUST initialize qlib with crypto data provider instead of traditional stock data
- **FR-003**: System MUST train machine learning models on crypto OHLCV data
- **FR-004**: System MUST generate trading signals using trained models and crypto datasets
- **FR-005**: System MUST perform signal analysis on crypto-generated signals
- **FR-006**: System MUST execute backtesting with crypto-specific trading parameters (0.1% maker/taker fees, 24/7 trading)
- **FR-007**: System MUST generate portfolio analysis reports with crypto-appropriate metrics
- **FR-008**: System MUST support crypto instrument universe configuration using top 50 symbols from config/top50_symbols.json
- **FR-009**: System MUST handle crypto data time frequencies (15 minutes) appropriately
- **FR-010**: System MUST log workflow parameters and save trained models for reproducibility

### Key Entities *(include if feature involves data)*

- **Crypto Instrument**: Represents a cryptocurrency trading pair (e.g., BTC/USDT), with attributes like symbol, base currency, quote currency
- **OHLCV Data**: Time series market data including open, high, low, close prices and volume for crypto instruments
- **Trained Model**: Machine learning model fitted on crypto data for signal generation
- **Trading Signal**: Model predictions converted to buy/sell signals for crypto instruments
- **Backtest Result**: Portfolio performance metrics from simulated trading on crypto data
- **Analysis Report**: Signal analysis and portfolio analysis outputs specific to crypto workflow

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a full crypto workflow (data loading to backtest results) in under 30 minutes for a typical dataset
- **SC-002**: System successfully trains models on crypto data with convergence rates above 95%
- **SC-003**: Generated backtest reports include all standard portfolio metrics (returns, Sharpe ratio, max drawdown) adapted for crypto
- **SC-004**: Signal analysis produces meaningful correlation and performance statistics for crypto instruments
- **SC-005**: Workflow script runs without errors and produces consistent results across multiple executions

## Assumptions

- Crypto data is available through existing qlib data collection mechanisms from OKX
- Standard machine learning models (GBDT) are suitable for crypto price prediction
- Backtesting parameters can be reasonably adapted from stock trading to crypto trading
- Backtesting covers the period from 2021-01-01 to 2024-01-01
- Configuration parameters will be stored in config/workflow.json
- Users have basic familiarity with qlib framework and Python scripting

## Clarifications

### Session 2025-11-08

- Q: Which crypto exchange/data source should be used for the workflow? → A: OKX
- Q: What specific crypto instruments should be included in the trading universe? → A: Top 50 symbols from config/top50_symbols.json
- Q: What time period should the backtesting cover? → A: 2021-01-01 to 2024-01-01
- Q: What time frequency should be used for the crypto data? → A: 15 minutes
- Q: What are the specific trading costs for crypto? → A: 0.1% maker/taker fees

## Dependencies

- Existing qlib framework and data collection infrastructure
- Access to crypto market data sources
- Python environment with required ML libraries
- Sufficient computational resources for model training

## Out of Scope

- Real-time crypto trading execution
- Advanced crypto-specific models (e.g., order book analysis)
- Multi-exchange arbitrage strategies
- DeFi protocol integration
