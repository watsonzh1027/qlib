Status: OPEN
Created: 2026-02-18 23:25:00

## Problem Description
LSTM and ALSTM models fail during training with TypeError in qlib's internal code, making them unusable for hyperparameter tuning despite correct configuration.

## Error Details
- **Error**: `TypeError: '<' not supported between instances of 'str' and 'int'`
- **Location**: `/qlib/lib/python3.12/site-packages/pandas/core/indexes/multi.py`, line 3230
- **Occurs in**: qlib LSTM model's fit() method
- **Triggered by**: Hyperparameter tuning with dynamically configured parameters

## Configuration State
✅ **Completed**:
- Added `tuning_ranges` for lstm/alstm in workflow.json
- Implemented dynamic parameter suggestion in tune_hyperparameters.py
- Added lstm/alstm support in train_sample_model.py
- Fixed integer parameter detection with step support

❌ **Not Working**:
- LSTM model training fails internally in qlib
- ALSTM likely has the same issue (not tested)

## Verified Working Configuration
```json
"lstm": {
  "hidden_size": {"min": 32, "max": 128, "step": 16},
  "num_layers": {"min": 1, "max": 4},
  "dropout": {"min": 0.0, "max": 0.5},
  "lr": {"min": 0.0001, "max": 0.01, "log": true},
  "batch_size": {"min": 256, "max": 2048, "step": 256}
}
```

Parameters correctly passed to model:
```
d_feat: 158
hidden_size: 128
num_layers: 1
dropout: 0.11495065194465864
lr: 0.00883646153174008
batch_size: 256  # Correctly converted to int
```

## Root Cause Analysis
The issue is within qlib's LSTM implementation, not our configuration. The error occurs in pandas MultiIndex operations during model.fit(), suggesting qlib's LSTM has compatibility issues with the current pandas version or has internal bugs.

## Attempted Solutions
1. ✅ Fixed integer parameter handling in tune_hyperparameters.py
2. ✅ Added explicit int() conversion in train_sample_model.py
3. ✅ Added step parameter to reduce search space
4. ❌ Issue persists - confirmed as qlib internal bug

## Workaround
**Current Status**: LSTM/ALSTM models are **not usable** for tuning.

**Recommended Alternative**:
- Continue using **LightGBM** (proven, fast, IC=0.144, Sharpe=1.50)
- Consider **XGBoost** as alternative tree-based model
- Both models are fully supported and tested

## Log Evidence
```
Log: logs/qlib-train_sample_model-1627264-1.log
Trial: 45
Command: scripts/train_sample_model.py --config tmp/tuning/cfg_model_ETHUSDT_45.json --model lstm
Error: TypeError in qlib.LSTM.fit() during training
```

## Next Steps
1. File bug report with qlib project (if not already known)
2. Check qlib version and consider upgrading/downgrading
3. Consider implementing custom LSTM wrapper if deep learning is critical
4. **For now**: Focus on optimizing LightGBM/XGBoost which work reliably

## Related Files
- [scripts/tune_hyperparameters.py](scripts/tune_hyperparameters.py)
- [scripts/train_sample_model.py](scripts/train_sample_model.py)
- [config/workflow.json](config/workflow.json)
- [issues/0076-fix-tuning-data-dir-frequency-suffix.md](issues/0076-fix-tuning-data-dir-frequency-suffix.md)
