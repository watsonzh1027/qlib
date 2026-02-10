# Funding Rate Collection Optimization

## Overview

Funding rates on OKX settle every **8 hours** at 00:00, 08:00, and 16:00 UTC. Collecting at 1-minute intervals creates 480x redundant data with no additional information.

## Changes Implemented

### 1. Time-Based Collection Window

**File:** `scripts/data_service.py`

- Added `_is_funding_collection_time()` method
- Only collects funding rates during 5-10 minute window after settlement (e.g., 00:05-00:10 UTC)
- Prevents wasteful API calls between settlements

**Configuration:**
```json
{
  "funding_collection_window_start": 5,  // Minutes after settlement to start
  "funding_collection_window_end": 10     // Minutes after settlement to end
}
```

### 2. Optimized Data Collection

**File:** `scripts/okx_data_collector.py`

- Updated documentation to clarify 8-hour native frequency
- Collection happens only at settlement times
- Reduces API calls from ~1,440/day to 3/day (99.8% reduction)

### 3. Forward-Fill Resampling

**File:** `scripts/convert_to_qlib.py`

**Key Change:** Funding rates are **forward-filled**, not aggregated.

**Before:**
```python
agg_dict['funding_rate'] = 'last'  # Incorrect - treats as continuous data
```

**After:**
```python
# Handle funding_rate separately with forward-fill
funding_resampled = funding_rate_col.resample(target_freq).ffill()
```

**Why:** Funding rates are discrete events (8-hour settlements), not continuous time-series. The rate remains constant until the next settlement, so we propagate the value forward.

### 4. Settlement Validation

**File:** `scripts/data_service.py`

- Added `_validate_funding_rate_settlements()` method
- Checks for missing settlements (should be exactly 3 per 24 hours)
- Warns if data gaps exist

### 5. Configuration Parameters

**File:** `config/workflow.json`

New parameters:
```json
{
  "data_service": {
    "funding_rate_native_interval": "8h",
    "funding_collection_times": ["00:05", "08:05", "16:05"],
    "funding_collection_window_start": 5,
    "funding_collection_window_end": 10
  }
}
```

## Collection Schedule

### Optimal Timing

| Settlement Time (UTC) | Collection Window | Rationale |
|-----------------------|-------------------|-----------|
| 00:00 | 00:05 - 00:10 | Allow 5-min API propagation delay |
| 08:00 | 08:05 - 08:10 | Allow 5-min API propagation delay |
| 16:00 | 16:05 - 16:10 | Allow 5-min API propagation delay |

### Data Service Behavior

1. **OHLCV Collection:** Runs every 2 minutes (configurable)
2. **Funding Rate Collection:** Only during settlement windows
3. **Combined Updates:** Both happen in same cycle during settlement windows

## Impact Analysis

### Before Optimization

- **Collection Frequency:** Every 60 seconds
- **Daily API Calls:** 1,440 per symbol
- **Annual Records:** 525,600 per symbol
- **Redundancy:** 480x duplicate data
- **Database Size:** Bloated with identical values

### After Optimization

- **Collection Frequency:** Every 8 hours (3x daily)
- **Daily API Calls:** 3 per symbol
- **Annual Records:** 1,095 per symbol
- **Redundancy:** 0% (only unique settlements)
- **Database Size:** 99.8% reduction

### Storage Comparison

```
1-minute collection:  525,600 records/year
8-hour collection:      1,095 records/year
Space saved:          524,505 records/year (99.79%)
```

## Data Flow

### 1. Collection (8-hour)

```
00:00 UTC → Funding Rate = 0.0001
08:00 UTC → Funding Rate = 0.00015
16:00 UTC → Funding Rate = 0.00012
```

### 2. Storage (PostgreSQL)

Only 3 records stored per day per symbol.

### 3. Conversion (Forward-Fill)

When converting to 1-hour timeframe:

```
00:00 → 0.0001 (from settlement)
01:00 → 0.0001 (forward-filled)
02:00 → 0.0001 (forward-filled)
...
07:00 → 0.0001 (forward-filled)
08:00 → 0.00015 (from settlement)
09:00 → 0.00015 (forward-filled)
...
```

### 4. Feature Engineering

Handler (`CryptoAlpha158WithFunding`) receives properly propagated funding rates at desired frequency.

## Verification

### Check Collection Status

```bash
python scripts/data_service.py status
```

Look for:
```
Funding Rate Collection: True
Next Update: <should align with settlement times>
```

### Verify Database Records

```sql
-- Should show ~3 records per day
SELECT 
    symbol,
    DATE(timestamp) as date,
    COUNT(*) as settlements,
    ARRAY_AGG(EXTRACT(HOUR FROM timestamp) ORDER BY timestamp) as hours
FROM funding_rates
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY symbol, DATE(timestamp)
ORDER BY date DESC;
```

Expected output:
```
symbol   | date       | settlements | hours
---------|------------|-------------|--------
ETHUSDT  | 2026-02-02 | 3           | {0, 8, 16}
ETHUSDT  | 2026-02-01 | 3           | {0, 8, 16}
```

### Validate Time Alignment

```python
import pandas as pd
from postgres_storage import PostgreSQLStorage
from postgres_config import PostgresConfig

# Load funding rates
storage = PostgreSQLStorage.from_config(...)
df = storage.get_funding_rates("ETHUSDT", start_time="2026-02-01", end_time="2026-02-02")

# Check settlement times
print(df['timestamp'].dt.hour.value_counts())
# Should show: 0, 8, 16 (each appearing once per day)
```

## Migration Guide

### For Existing Installations

If you have existing 1-minute funding rate data:

**Option 1: Keep Historical Data**
- Leave old data as-is
- New collection uses 8-hour intervals going forward
- Forward-fill handles both old and new data correctly

**Option 2: Deduplicate Historical Data**
```python
# Keep only settlement times (00:00, 08:00, 16:00)
DELETE FROM funding_rates 
WHERE EXTRACT(HOUR FROM timestamp) NOT IN (0, 8, 16);
```

**Option 3: Fresh Start**
```sql
-- Clear all funding rate data
TRUNCATE TABLE funding_rates;
```

Then run:
```bash
# Collect last 30 days
python scripts/data_service.py run-once
```

## Troubleshooting

### No Funding Rate Data Collected

**Check:** Current time vs. collection window
```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
print(f"Current UTC time: {now.hour:02d}:{now.minute:02d}")
print(f"Is settlement hour: {now.hour in [0, 8, 16]}")
print(f"Is collection minute: {5 <= now.minute < 10}")
```

### Missing Settlements

**Check:** Service was running during collection window
```bash
# View service logs
tail -f logs/data_service.log | grep funding
```

**Check:** Database for gaps
```sql
SELECT 
    symbol,
    timestamp,
    LAG(timestamp) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_timestamp,
    EXTRACT(EPOCH FROM (timestamp - LAG(timestamp) OVER (PARTITION BY symbol ORDER BY timestamp)))/3600 as hours_gap
FROM funding_rates
WHERE symbol = 'ETHUSDT'
ORDER BY timestamp DESC
LIMIT 20;
```

Expected `hours_gap`: ~8.0 hours between settlements

### Forward-Fill Not Working

**Check:** Timeframe alignment in conversion
```bash
python scripts/convert_to_qlib.py --source db --timeframes 15min 60min --symbols ETHUSDT
```

Look for log messages:
```
Forward-filling funding_rate from 8-hour to 15min
```

## Best Practices

1. **Run Service Continuously:** Ensure data service is running 24/7 to catch all settlements
2. **Monitor Logs:** Check for missing settlement warnings
3. **Validate Weekly:** Run settlement validation to detect gaps
4. **Align Timeframes:** Use timeframes that are divisors of 8 hours (1h, 2h, 4h work best)
5. **Historical Backfill:** When starting, backfill as much historical data as OKX API allows (~3 months)

## References

- OKX Funding Rate API: `/api/v5/public/funding-rate-history`
- Settlement Times: 00:00, 08:00, 16:00 UTC daily
- API Historical Limit: ~3 months
- Records per Settlement: 1 per symbol per settlement time

## Summary

This optimization aligns data collection with exchange settlement mechanics:

✅ **Accurate:** Represents true 8-hour funding rate frequency  
✅ **Efficient:** 99.8% reduction in API calls and storage  
✅ **Compatible:** Forward-fill handles all timeframe conversions  
✅ **Validated:** Automatic detection of missing settlements  
✅ **Configurable:** Easy to adjust collection windows  

The funding rate collection now operates at its **native 8-hour frequency**, eliminating redundancy while maintaining full data fidelity.
