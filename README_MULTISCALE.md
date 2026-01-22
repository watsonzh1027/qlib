# Multi-Scale Crypto Trading Strategy - Quick Start Guide

## Overview

Multi-timeframe trading strategy using Qlib framework with XGBoost model for ETH_USDT prediction.

## Quick Start

### 1. Train Model
```bash
# Activate environment
conda activate qlib

# Train XGBoost model (recommended)
python scripts/train_multiscale.py --timeframe 60min --model xgb --eval_ic --n_jobs 8

# Train other models
python scripts/train_multiscale.py --timeframe 60min --model lgb --eval_ic --n_jobs 8  # LightGBM
python scripts/train_multiscale.py --timeframe 60min --model mlp --eval_ic           # MLP
```

### 2. Hyperparameter Tuning
```bash
# Tune XGBoost (15 trials)
python scripts/tune_multiscale.py --timeframe 60min --model xgb --n_trials 15

# Results saved to: config/tuned_params_60min_xgb.json
```

### 3. Run Backtest
```bash
python scripts/run_multiscale_backtest.py
```

## Model Performance

| Model | IC (Validation) | Recommendation |
|-------|----------------|----------------|
| XGBoost | 0.021 | ✅ **Recommended** |
| LightGBM | 0.009 | ⚠️ Alternative |
| MLP | -0.031 | ❌ Not recommended |
| CatBoost | -0.002 | ❌ Not recommended |

## Configuration

### Main Config: `config/workflow_multiscale.json`

**Key Settings**:
- **Model**: `"model_type": "xgb"`
- **Data**: ETH_USDT, 60min frequency
- **Features**: Alpha158 + 4 custom time features (sin/cos weekday/hour)
- **Pipeline**: RobustZScoreNorm → Fillna → CleanNaNInf

### XGBoost Parameters (Optimized)
```json
{
  "learning_rate": 0.088,
  "max_depth": 4,
  "min_child_weight": 6,
  "subsample": 0.50,
  "colsample_bytree": 0.98,
  "reg_alpha": 2.5e-05,
  "reg_lambda": 4.3e-05
}
```

## Project Structure

```
qlib/
├── config/
│   └── workflow_multiscale.json      # Main configuration
├── scripts/
│   ├── train_multiscale.py           # Training script
│   ├── tune_multiscale.py            # Hyperparameter tuning
│   └── run_multiscale_backtest.py    # Backtesting
├── models/multiscale/                # Saved models
├── qlib/contrib/
│   ├── data/processor_clean.py       # NaN/Inf cleaner
│   └── model/
│       ├── mlp.py                    # MLP model
│       └── simple_lstm.py            # Simplified LSTM
└── data/qlib_data/crypto_60min/      # Market data
```

## Custom Features

Added time-based features using custom operators:
- `Sin(Weekday)` / `Cos(Weekday)` - Day of week cyclical encoding
- `Sin(Hour)` / `Cos(Hour)` - Hour of day cyclical encoding

Operators registered in: `qlib/data/ops.py`

## Data Preprocessing Pipeline

**Critical Fix**: Added `CleanNaNInf` processor to handle NaN/Inf values:

```json
{
  "infer_processors": [
    {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": true}},
    {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
    {"class": "CleanNaNInf", "module_path": "qlib.contrib.data.processor_clean"}
  ]
}
```

## Known Issues & Solutions

### Issue: NaN in Neural Network Training
**Symptom**: MLP/LSTM shows NaN loss  
**Cause**: NaN/Inf in input features  
**Solution**: `CleanNaNInf` processor added to pipeline

### Issue: LSTM Training Fails
**Symptom**: Shape mismatch or NaN  
**Cause**: LSTM expects sequential data, not aggregated Alpha158  
**Solution**: Use tree models (XGBoost/LightGBM) or implement sequential data loader

## Next Steps

1. **Improve IC**: Add more features, try multi-asset approach
2. **Backtest**: Validate strategy with realistic trading simulation
3. **Risk Management**: Implement stop-loss and position sizing
4. **Deployment**: Set up live trading pipeline

## References

- **Qlib Documentation**: https://qlib.readthedocs.io/
- **XGBoost**: https://xgboost.readthedocs.io/
- **Alpha158 Features**: Qlib's default 158 technical indicators

## Support

For issues or questions, check:
- `logs/` directory for training logs
- `issues/` directory for documented problems
- Model comparison summary: `brain/.../walkthrough.md`
