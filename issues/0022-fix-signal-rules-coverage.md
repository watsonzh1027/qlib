# Issue 0022: Fix signal_rules.py coverage measurement

## Problem
The pytest coverage command `--cov=features/crypto_workflow/signal_rules` was failing to measure coverage for `signal_rules.py`. The log showed:
- Warning: "Module features/crypto_workflow/signal_rules was never imported."
- Warning: "No data was collected."
- Coverage report did not include `signal_rules.py`

## Root Cause
pytest-cov attempts to import the specified modules at the start of test execution to set up coverage tracing. However, the specific module path `features/crypto_workflow/signal_rules` could not be imported because the test file modifies `sys.path` during test execution, not before.

## Solution
Changed the coverage argument from `--cov=features/crypto_workflow/signal_rules` to `--cov=features` to cover the entire features package. This allows coverage to be collected for `signal_rules.py` when it's actually imported during test execution.

## Command Change
```bash
# Before (not working)
pytest tests/test_signal_rules.py -v --cov=features/crypto_workflow/signal_rules --cov-report=term-missing

# After (working)
pytest tests/test_signal_rules.py -v --cov=features --cov-report=term-missing
```

## Result
- `features/crypto_workflow/signal_rules.py` now shows 100% coverage (21/21 statements covered)
- Tests pass successfully
- Coverage data is properly collected

## Files Modified
- None (command line change only)

## Tests Verified
- `test_score_to_signal_basic` - PASSED
- `test_score_to_signal_custom_thresholds` - PASSED
