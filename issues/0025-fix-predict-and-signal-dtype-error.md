# Issue 0025: Fix predict_and_signal.py dtype error

## Problem Description
When running the predict_and_signal.py script, a ValueError was raised because LightGBM requires only numeric dtypes (int, float, bool) for prediction, but the features DataFrame contained object dtypes for 'symbol' and 'timeframe' columns.

Error:
```
ValueError: pandas dtypes must be int, float or bool.
Fields with bad pandas dtypes: symbol: object, timeframe: object
```

## Root Cause
The script was passing the entire features DataFrame to the model's predict method, including non-numeric columns like 'symbol' and 'timeframe'.

## Solution
Modified `examples/predict_and_signal.py` to select only numeric columns before prediction:

1. Added import for numpy: `import numpy as np`
2. Changed the prediction line to use only numeric features:
   ```python
   # Select only numeric columns for prediction (LightGBM requirement)
   numeric_features = features_df.select_dtypes(include=[np.number])
   
   # Generate predictions
   scores = model.predict(numeric_features)
   ```

## Files Changed
- `examples/predict_and_signal.py`: Added numpy import and modified prediction logic to filter numeric columns.

## Testing
- Ran the script with the original command:
  ```bash
  python examples/predict_and_signal.py \
    --model-path models/btc_lgb.pkl \
    --features-path data/features/features_btc_1h.parquet \
    --output-path signals/btc_signals.parquet
  ```
- Script executed successfully without errors.
- Output file `signals/btc_signals.parquet` was generated.

## Notes
- The 'symbol' and 'timeframe' columns are still used in the signals DataFrame creation for context, but not passed to the model.
- This fix ensures compatibility with LightGBM's dtype requirements while preserving necessary metadata in the output signals.
