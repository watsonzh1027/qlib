# Issue 0004: Fix train_validate implementation

## Problem Description
The `train_validate` method in `LGBTrainer` was a placeholder returning `None` for model and only basic metrics, causing `test_model_training_validation` to fail with KeyError for 'precision'.

## Root Cause
The method was not implemented properly; it didn't train the model or calculate the required metrics like precision, recall, f1.

## Solution
Implemented the `train_validate` method to:
- Train a LightGBM model with validation data
- Calculate accuracy, precision, recall, f1, and sharpe metrics
- Return the trained model and metrics dictionary

## Testing
Ran `pytest tests/test_model.py::test_model_training_validation -v` and it passed.

## Files Changed
- `qlib/model/crypto/LGBTrainer.py`: Implemented proper `train_validate` method.

## Next Steps
Proceed to fix the next error: Add `save` and `load` methods to `LGBTrainer` for persistence tests.
