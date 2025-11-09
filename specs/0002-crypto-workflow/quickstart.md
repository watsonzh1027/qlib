# Quickstart: Crypto Workflow

**Feature**: 0002-crypto-workflow
**Date**: 2025-11-08

## Overview

This guide shows how to run the complete crypto trading workflow using the adapted qlib framework. The workflow loads crypto data, trains a model, generates signals, and performs backtesting.

## Prerequisites

- Python 3.x with qlib environment activated
- Data available in `data/qlib_data/crypto` (OHLCV format)
- Top 50 symbols configured in `config/top50_symbols.json`
- Workflow parameters configured in `config/workflow.json`

## Quick Start

### 1. Activate Environment
```bash
conda activate qlib
```

### 2. Configure Parameters
Edit `config/workflow.json` to set workflow parameters:

```json
{
  "workflow": {
    "start_time": "2021-01-01",
    "end_time": "2024-01-01",
    "frequency": "15min"
  },
  "backtest": {
    "initial_capital": 1000000,
    "open_cost": 0.001,
    "close_cost": 0.001
  }
}
```

### 3. Run the Workflow
```bash
cd /home/watson/work/qlib-crypto
python examples/workflow_crypto.py
```

### 3. View Results
The workflow will:
- Load crypto data from OKX (top 50 instruments)
- Train GBDT model on 15-minute data (2021-2024)
- Generate trading signals
- Run backtesting with crypto fees (0.1%)
- Produce analysis reports

Results are saved in the experiment recorder and include:
- Model performance metrics
- Signal analysis charts
- Portfolio backtesting results (Sharpe ratio, max drawdown, returns)

## Expected Output

```
Loading crypto data...
Training model...
Generating signals...
Running backtest...
Analysis complete.

Results:
- Total Return: X.XX%
- Sharpe Ratio: X.XX
- Max Drawdown: X.XX%
- Win Rate: XX.X%
```

## Configuration

The workflow uses these default settings:
- **Data Source**: OKX exchange
- **Instruments**: Top 50 from config/top50_symbols.json
- **Time Period**: 2021-01-01 to 2024-01-01
- **Frequency**: 15 minutes
- **Model**: GBDT (LightGBM)
- **Trading Fees**: 0.1% maker/taker
- **Strategy**: Top 50 long, drop 5 worst

## Customization

To modify parameters, edit `config/workflow.json`:

```json
{
  "workflow": {
    "start_time": "2022-01-01",
    "end_time": "2023-01-01",
    "frequency": "1d"
  },
  "backtest": {
    "initial_capital": 500000,
    "open_cost": 0.002,
    "close_cost": 0.002
  }
}
```

The workflow uses `scripts/config_manager.py` to load and manage all parameters centrally.

## Troubleshooting

### Data Loading Issues
- Ensure `data/qlib_data/crypto` exists and contains OHLCV data
- Check qlib data format compatibility

### Model Training Failures
- Verify sufficient data for the time period
- Check model configuration parameters

### Backtesting Errors
- Confirm crypto-specific parameters (24/7 trading, fees)
- Validate signal data format

### Performance Issues
- Reduce instrument count for faster processing
- Use shorter time periods for testing

## Next Steps

- Review analysis reports for model insights
- Adjust strategy parameters based on results
- Extend workflow for live trading (future feature)
- Add custom indicators or models

## Support

For issues:
1. Check qlib documentation
2. Review error logs in experiment recorder
3. Validate data integrity in `data/qlib_data/crypto`