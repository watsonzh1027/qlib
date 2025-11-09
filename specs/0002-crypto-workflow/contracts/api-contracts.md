# API Contracts: Crypto Workflow

**Feature**: 0002-crypto-workflow
**Date**: 2025-11-08
**Format**: Internal Python function contracts

## Configuration Management API

### ConfigManager.load_config() -> Dict
**Purpose**: Load workflow configuration from config/workflow.json

**Returns**: Dictionary with all workflow parameters

**Preconditions**:
- config/workflow.json exists with crypto workflow parameters

**Postconditions**:
- Configuration includes data paths, backtest parameters, model settings

**Configuration Structure**:
```json
{
  "data": {
    "csv_data_dir": "data/klines",
    "bin_data_dir": "data/qlib_data/crypto",
    "symbols": "config/top50_symbols.json"
  },
  "workflow": {
    "start_time": "2021-01-01",
    "end_time": "2024-01-01",
    "frequency": "15min",
    "instruments_limit": 50
  },
  "model": {
    "type": "GBDT",
    "learning_rate": 0.1,
    "num_boost_round": 100
  },
  "backtest": {
    "initial_capital": 1000000,
    "open_cost": 0.001,
    "close_cost": 0.001,
    "min_cost": 0.001,
    "strategy_topk": 50,
    "strategy_n_drop": 5
  }
}
```

## Data Loading API

### load_crypto_data(provider_uri: str, instruments: List[str]) -> pd.DataFrame
**Purpose**: Load OHLCV data for specified crypto instruments from qlib data provider

**Parameters**:
- `provider_uri` (str): Path to qlib data directory (e.g., "data/qlib_data/crypto")
- `instruments` (List[str]): List of instrument symbols to load

**Returns**: DataFrame with OHLCV data indexed by timestamp and instrument

**Preconditions**:
- Data directory exists and contains qlib-formatted data
- Instruments are valid crypto symbols

**Postconditions**:
- DataFrame contains 15-minute OHLCV data for 2021-2024 period
- Missing data periods are handled gracefully

## Model Training API

### train_crypto_model(dataset: qlib.data.Dataset, model_config: Dict) -> qlib.model.Model
**Purpose**: Train machine learning model on crypto dataset

**Parameters**:
- `dataset` (qlib.data.Dataset): Prepared dataset with crypto features
- `model_config` (Dict): Model configuration (GBDT parameters)

**Returns**: Trained model ready for prediction

**Preconditions**:
- Dataset contains valid crypto OHLCV data
- Model config specifies supported algorithm

**Postconditions**:
- Model converges and achieves reasonable training metrics
- Model can generate predictions on new data

## Signal Generation API

### generate_trading_signals(model: qlib.model.Model, dataset: qlib.data.Dataset) -> pd.DataFrame
**Purpose**: Generate trading signals using trained model

**Parameters**:
- `model` (qlib.model.Model): Trained prediction model
- `dataset` (qlib.data.Dataset): Dataset for signal generation

**Returns**: DataFrame with trading signals (-1 to 1 scale)

**Preconditions**:
- Model is trained and compatible with dataset
- Dataset contains future/prediction periods

**Postconditions**:
- Signals are bounded [-1, 1]
- Signal timestamps align with data intervals

## Backtesting API

### run_crypto_backtest(signals: pd.DataFrame, config: Dict) -> Dict
**Purpose**: Execute backtesting with crypto-specific parameters

**Parameters**:
- `signals` (pd.DataFrame): Trading signals from model
- `config` (Dict): Backtest configuration with crypto parameters

**Returns**: Dictionary with portfolio performance metrics

**Preconditions**:
- Signals contain valid trading signals
- Config includes crypto-appropriate fees (0.1%) and 24/7 trading

**Postconditions**:
- Results include Sharpe ratio, max drawdown, total returns
- Metrics are calculated for crypto market context

**Config Structure**:
```python
{
    "executor": {
        "class": "SimulatorExecutor",
        "kwargs": {"time_per_step": "15min", "generate_portfolio_metrics": True}
    },
    "strategy": {
        "class": "TopkDropoutStrategy",
        "kwargs": {"topk": 50, "n_drop": 5}
    },
    "backtest": {
        "start_time": "2021-01-01",
        "end_time": "2024-01-01",
        "account": 1000000,
        "exchange_kwargs": {
            "open_cost": 0.001,  # 0.1% maker fee
            "close_cost": 0.001, # 0.1% taker fee
            "min_cost": 0.001
        }
    }
}
```

## Analysis API

### analyze_crypto_signals(signals: pd.DataFrame) -> Dict
**Purpose**: Perform signal analysis on crypto trading signals

**Parameters**:
- `signals` (pd.DataFrame): Trading signals to analyze

**Returns**: Dictionary with signal analysis metrics

**Preconditions**:
- Signals contain valid data

**Postconditions**:
- Analysis includes correlation, performance statistics
- Metrics appropriate for crypto instruments

### analyze_portfolio_results(backtest_results: Dict) -> Dict
**Purpose**: Analyze portfolio backtesting results

**Parameters**:
- `backtest_results` (Dict): Results from backtesting

**Returns**: Dictionary with portfolio analysis metrics

**Preconditions**:
- Backtest results are valid

**Postconditions**:
- Analysis includes risk metrics, performance attribution
- Results formatted for crypto trading context

## Error Handling

All APIs follow qlib error handling conventions:
- Invalid inputs raise ValueError with descriptive messages
- Data loading failures raise IOError
- Model failures raise RuntimeError
- All exceptions include context about the operation

## Performance Contracts

- Data loading: < 5 minutes for top 50 instruments
- Model training: < 10 minutes on standard hardware
- Signal generation: < 2 minutes
- Backtesting: < 10 minutes
- Analysis: < 1 minute

## Version Compatibility

- Compatible with qlib v0.1+ data format
- Supports Python 3.8+ type hints
- Maintains backward compatibility with existing qlib workflows