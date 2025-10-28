# Data Model: Crypto Trading Workflow

## Raw Data Schema

### OHLCV Data
- Path: data/raw/{exchange}/{symbol}/{interval}/YYYY-MM-DD.parquet
```python
{
    "timestamp": "datetime64[ns, UTC]",  # Interval boundary
    "open": "float64",     # First trade price
    "high": "float64",     # Highest trade price
    "low": "float64",      # Lowest trade price
    "close": "float64",    # Last trade price
    "volume": "float64",   # Trading volume in quote currency
}
```

### Data Manifest
- Path: data/raw/{exchange}/{symbol}/manifest.json
```json
{
    "exchange_id": "okx",
    "symbol": "BTC-USDT",
    "interval": "15min",
    "start_timestamp": "2022-01-01T00:00:00Z",
    "end_timestamp": "2024-01-01T00:00:00Z",
    "fetch_timestamp": "2024-01-09T00:00:00Z",
    "version": "1.0.0",
    "row_count": 70080
}
```

## Processed Data Schema

### Feature Set
- Path: features/{symbol}/{interval}/v{YYYYMMDD}.{NNN}.parquet
```python
{
    "timestamp": "datetime64[ns, UTC]",
    "target": "float32",           # Binary label (1: up, 0: down)
    "feature_*": "float32",        # Generated features
    "is_valid": "bool",           # Data quality flag
}
```

## Model Artifacts

### Model File Structure
- Main model: models/{symbol}/{interval}/v{YYYYMMDD}.{NNN}.bin
- Parameters: models/{symbol}/{interval}/v{YYYYMMDD}.{NNN}.txt
- Metadata: models/{symbol}/{interval}/v{YYYYMMDD}.{NNN}.json

### Model Metadata Schema
```json
{
    "model_id": "BTC-USDT-15min-20240109001",
    "model_version": "v20240109.001",
    "training_start": "2023-01-01T00:00:00Z",
    "training_end": "2023-12-31T23:59:59Z",
    "parameters": {
        "num_leaves": 31,
        "learning_rate": 0.05
    },
    "metrics": {
        "accuracy": 0.57,
        "sharpe": 1.4,
        "max_drawdown": 0.22
    }
}
```

## Signal & Backtest Output

### Trading Signals
- Path: signals/{model_id}/YYYY-MM-DD.csv
```python
{
    "timestamp": "datetime64[ns, UTC]",
    "symbol": "str",
    "signal": "category",        # BUY, SELL, HOLD
    "score": "float32",         # Model output [0,1]
    "position_size": "float32"  # % of capital [0,1]
}
```

### Backtest Results
- Path: backtest/{model_id}/report.json
```json
{
    "model_id": "BTC-USDT-15min-20240109001",
    "period_start": "2023-01-01T00:00:00Z",
    "period_end": "2023-12-31T23:59:59Z",
    "metrics": {
        "sharpe_ratio": 1.4,
        "max_drawdown": 0.22,
        "win_rate": 0.54,
        "profit_factor": 1.35
    },
    "assumptions": {
        "fee_rate": 0.0005,
        "slippage": 0.0005,
        "min_trade_value": 100,
        "max_position": 1.0
    }
}
```
