# Issue 0001: Fix Log Levels Assertion in `test_logging.py`

## Problem Description

The test case `test_log_levels` in `tests/test_logging.py` was failing with the following error:
```
AssertionError: assert 'Debug message' in [{'level': 'DEBUG', 'logger': 'test', 'message': 'Debug message', 'timestamp': '2025-10-25T23:06:02.302977'}, ...]
```

The issue was that the assertion was checking if the string `"Debug message"` was directly in the `logs.records` list, but `logs.records` is a list of dictionaries, each containing fields like `level`, `logger`, `message`, and `timestamp`.

## Solution

The assertion was modified to correctly check the `message` field of each record in `logs.records`:
```python
assert any(record["message"] == "Debug message" for record in logs.records)
assert any(record["message"] == "Error message" for record in logs.records)
```

## Verification

After the change, the test passed successfully:
```
tests/test_logging.py::test_log_levels PASSED
```

## Notes

This issue highlights the importance of understanding the structure of the data being tested. The fix ensures that the test correctly validates the log messages.