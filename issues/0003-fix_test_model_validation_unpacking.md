# Issue 0003: Fix test_model_validation unpacking

## Problem Description
In `test_model_validation`, the `trainer.train_validate` method returns a tuple `(model, metrics)`, but the test was assigning it to a single variable `metrics`, causing `assert "accuracy" in metrics` to fail because `metrics` was the tuple itself.

## Root Cause
The test code was not unpacking the return value correctly. The method returns `(model, metrics)`, but the test treated it as returning just `metrics`.

## Solution
Modified the test to unpack the return value:
```python
model, metrics = trainer.train_validate(...)
```

## Testing
Ran the specific test `pytest tests/test_model.py::test_model_validation -v` and it passed.

## Files Changed
- `tests/test_model.py`: Fixed unpacking in `test_model_validation`.

## Next Steps
Proceed to fix the next error: `test_model_training_validation` which has a KeyError for 'precision'.
