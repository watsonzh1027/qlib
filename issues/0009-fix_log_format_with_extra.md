# Issue 0009: Fix log format with extra attributes

## Problem Description
The test `test_log_format_with_extra` in `tests/test_logging.py` was failing because the `JsonFormatter` in `qlib/utils/logging.py` was not properly including extra attributes passed to the logger in the JSON output.

The assertion `assert "key" in record` was failing because the extra `{"key": "value"}` was not being included in the log record dictionary.

## Root Cause
The original code checked for `hasattr(record, "extra") and record.extra`, but when logging with `extra={"key": "value"}`, the extra attributes are set directly on the record object, not in a separate `extra` attribute.

## Solution
Modified the `JsonFormatter.format` method to dynamically include all non-standard attributes from `record.__dict__` in the log data. This ensures that any extra attributes passed via the `extra` parameter are included in the JSON output.

### Changes Made
- Updated `JsonFormatter.format` to collect extra keys by excluding standard logging record attributes.
- Added a loop to include these extra keys in the `log_data` dictionary.

### Code Changes
```python
# Before
if hasattr(record, "extra") and record.extra:
    log_data.update(record.extra)

# After
# Include extra attributes from record.__dict__
standard_keys = {
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
    'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
    'processName', 'process'
}
extra_keys = set(record.__dict__.keys()) - standard_keys
for key in extra_keys:
    log_data[key] = record.__dict__[key]
```

## Testing
- Ran the specific failing test: `pytest tests/test_logging.py::test_log_format_with_extra` - PASSED
- Ran all logging tests: `pytest tests/test_logging.py --cov=qlib.utils.logging` - All 5 tests PASSED, coverage 100%

## Files Modified
- `qlib/utils/logging.py`: Updated `JsonFormatter.format` method

## Files Created
- This issue file: `issues/0009-fix_log_format_with_extra.md`
