# Issue 0021: Fix LightGBM Early Stopping API Compatibility

## Problem Description
The test `test_train_lgb_end_to_end` in `tests/test_train_lgb.py` was failing with the error:
```
TypeError: train() got an unexpected keyword argument 'early_stopping_rounds'
```

This occurred because the code in `features/crypto_workflow/train_utils.py` was using an outdated API for LightGBM's `lgb.train()` function. In newer versions of LightGBM, the `early_stopping_rounds` parameter has been removed from the direct arguments and must be passed via the `callbacks` parameter using `lgb.early_stopping(early_stopping_rounds)`.

## Root Cause
The `fit` method in the `LGBModel` class was calling:
```python
self.model = lgb.train(
    self.params,
    train_data,
    valid_sets=[valid_data] if valid_data else None,
    early_stopping_rounds=early_stopping_rounds,  # This parameter is no longer supported
    callbacks=[lgb.log_evaluation(period=100)]
)
```

## Solution
Modified the `fit` method to use the correct callback-based API:
```python
callbacks = [lgb.log_evaluation(period=100)]
if valid_data is not None:
    callbacks.append(lgb.early_stopping(early_stopping_rounds))

self.model = lgb.train(
    self.params,
    train_data,
    valid_sets=[valid_data] if valid_data else None,
    callbacks=callbacks
)
```

## Files Changed
- `features/crypto_workflow/train_utils.py`: Updated the `fit` method to use `lgb.early_stopping` callback instead of the deprecated `early_stopping_rounds` parameter.

## Testing
- Ran `pytest tests/test_train_lgb.py -v` and confirmed the test now passes.
- The fix ensures compatibility with current LightGBM versions while maintaining the same functionality.

## Verification
The test suite now runs successfully:
```
tests/test_train_lgb.py::test_train_lgb_end_to_end PASSED
