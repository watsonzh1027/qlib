# Issue 0038: Configure logging to save to logs directory and centralize config

## Status: CLOSED
## Created: 2025-11-08 14:00:00

## Problem Description
The logging configuration was hardcoded in `workflow_crypto.py` and only output to console. There was no persistent logging to files in the logs directory, making debugging difficult.

## Root Cause
- Logging was configured with `logging.basicConfig()` only for console output
- No file logging was implemented
- Configuration was hardcoded instead of centralized in `workflow.json`

## Solution Implemented
Modified qlib's logging configuration in `qlib/config.py` to add file logging:

1. **Added file handler to qlib logging config**:
   - Added "file" handler that writes to "logs/qlib.log"
   - Updated qlib logger to use both "console" and "file" handlers
   - File logging uses the same formatter and filters as console logging

2. **Removed custom logging configuration**:
   - Removed logging config from `workflow.json`
   - Removed `get_logging_config()` method from `ConfigManager`
   - Reverted `workflow_crypto.py` to use standard qlib logging

## Files Changed
- `qlib/config.py`: Added file handler to logging_config and updated qlib logger handlers
- `config/workflow.json`: Removed logging configuration section
- `scripts/config_manager.py`: Removed `get_logging_config()` method
- `examples/workflow_crypto.py`: Reverted to standard qlib logging setup

## Testing
- Verified that logs directory is created automatically by qlib
- Confirmed that log messages are written to both console and `logs/qlib.log`
- Workflow runs successfully with qlib's built-in logging configuration

## Resolution Time
Started: 2025-11-08 14:00:00
Completed: 2025-11-08 14:45:00