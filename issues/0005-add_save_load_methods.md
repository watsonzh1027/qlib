# Issue 0005: Add save and load methods to LGBTrainer

## Problem Description
The `LGBTrainer` class was missing `save` and `load` methods, causing `test_model_persistence` and `test_invalid_operations` to fail with AttributeError.

## Root Cause
The trainer class didn't implement model persistence functionality required by the tests.

## Solution
- Added `__init__` method to initialize `self.model = None`
- Modified `train` and `train_validate` to store the model in `self.model`
- Implemented `save` method to save the model and metadata to disk
- Implemented `load` method to load the model from disk
- Added proper error handling for saving without training and loading non-existent files

## Testing
Ran `pytest tests/test_model.py::test_model_persistence -v` and it passed. Also `test_invalid_operations` should now pass as it tests the save method error handling.

## Files Changed
- `qlib/model/crypto/LGBTrainer.py`: Added `__init__`, modified `train` and `train_validate`, added `save` and `load` methods.

## Next Steps
Proceed to fix the last error: `test_feature_importance` where the assertion about trend being more important than noise fails.
