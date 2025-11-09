# Issue 0029: Fix OKX Data Collector Earlier Data Download

**Status:** CLOSED  
**Created:** 2025-11-08 10:00:00  

## Problem Description

The `scripts/okx_data_collector.py` script has a bug where it cannot download earlier data when the start time in `workflow.json` is earlier than the first record in the existing CSV file. The code only appends new data and does not handle cases where historical data needs to be fetched and prepended to the existing data.

### Root Cause
- The `calculate_fetch_window` function only checked the last timestamp of existing data.
- If the last timestamp covered the requested end time, it would skip fetching, even if the start time required earlier data.
- No mechanism to detect if the requested start time was before the first existing record.

## Final Solution

### Changes Made

1. **Added `get_first_timestamp_from_csv` function**:
   - Reads the first data record's timestamp from the CSV file.
   - Similar to `get_last_timestamp_from_csv` but for the earliest timestamp.

2. **Modified `calculate_fetch_window` logic**:
   - Now retrieves both first and last timestamps from existing data.
   - Checks if existing data fully covers the requested range (first_ts <= req_start and last_ts >= req_end).
   - If earlier data is needed (req_start < first_ts), sets adjusted_start to req_start.
   - Otherwise, uses the original logic with overlap adjustment.

3. **Data Merging**:
   - The existing merge logic in `update_latest_data` already handles prepending earlier data.
   - When new data includes earlier timestamps, `can_append` is set to False, causing a full file rewrite with sorted data.

### Code Changes

```python
def get_first_timestamp_from_csv(symbol: str, base_dir: str = "data/klines") -> pd.Timestamp | None:
    # Implementation to read first timestamp from CSV
    ...

def calculate_fetch_window(symbol: str, requested_start: str, requested_end: str, base_dir: str = "data/klines") -> tuple[str, str, bool]:
    last_timestamp = get_last_timestamp_from_csv(symbol, base_dir)
    first_timestamp = get_first_timestamp_from_csv(symbol, base_dir)
    
    if last_timestamp is None or first_timestamp is None:
        return requested_start, requested_end, True
    
    # Parse times...
    
    # Check full coverage
    if first_timestamp <= req_start_ts and last_timestamp >= req_end_ts:
        return requested_start, requested_end, False
    
    # Determine if earlier data needed
    need_earlier = req_start_ts < first_timestamp
    
    if need_earlier:
        adjusted_start = req_start_ts
    else:
        adjusted_start = max(req_start_ts, last_timestamp - overlap_delta)
    
    return adjusted_start.isoformat(), requested_end, True
```

## Update Log

- **2025-11-08 10:00:00**: Identified the issue - code skips fetching when last timestamp covers end time, ignoring earlier start time requirements.
- **2025-11-08 10:05:00**: Added `get_first_timestamp_from_csv` function to read earliest timestamp.
- **2025-11-08 10:10:00**: Modified `calculate_fetch_window` to check both first and last timestamps, enabling earlier data fetching.
- **2025-11-08 10:15:00**: Verified merge logic handles prepending data correctly via full file rewrite when needed.
- **2025-11-08 10:20:00**: Compiled code successfully, no syntax errors. Issue resolved.