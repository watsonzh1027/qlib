# Funding Rate is 0.0 - Troubleshooting Guide

## Problem

Your converted data shows `funding_rate` as `0.0` for all rows:

```csv
timestamp,symbol,open,high,low,close,volume,interval,vwap,funding_rate
2020-01-01 00:00:00+00:00,ETHUSDT,129.19,129.19,129.03,129.04,136.362165,1m,129.11249999999998,0.0
2020-01-01 00:01:00+00:00,ETHUSDT,129.04,129.11,129.03,129.07,18.552363,1m,129.0625,0.0
```

## Root Causes

### 1. **CSV Files Don't Contain Funding Rates**

The OHLCV CSV files in `data/klines/{SYMBOL}/` only contain price and volume data:
- `timestamp, symbol, open, high, low, close, volume, interval, vwap`
- **Missing:** `funding_rate` column

### 2. **Funding Rates Stored Separately**

When using CSV output format:
- OHLCV data → `data/klines/{SYMBOL}/1m.csv`
- Funding rates → PostgreSQL `funding_rates` table (if `database.use_db` = true)
- **No automatic merging** happens during collection

### 3. **Historical Data Limitation**

Your data is from **2020-01-01**:
- OKX API only provides ~3 months of historical funding rate data
- 2020 data predates your funding rate collection
- Even if you collect now, you can't backfill 2020 funding rates from OKX API

### 4. **Conversion Process Limitation**

`convert_to_qlib.py` has two paths:
- **CSV path**: Reads CSV files directly, expects `funding_rate` column already present
- **Database path**: Fetches OHLCV + merges funding rates from PostgreSQL (now fixed)

## Solutions

### Solution 1: Use Database Storage (Recommended)

**Best for:** New data collection going forward

**Steps:**

1. **Update configuration** to use database output:

```json
{
  "data_collection": {
    "output": "db"  // Change from "csv" to "db"
  },
  "database": {
    "use_db": true
  },
  "data_convertor": {
    "data_source": "db"  // Change from "csv" to "db"
  }
}
```

2. **Collect new data** (will store in PostgreSQL):

```bash
# Start data service (collects both OHLCV and funding rates)
python scripts/data_service.py start

# Or run once manually
python scripts/data_service.py run-once
```

3. **Convert from database** (now properly merges funding rates):

```bash
python scripts/convert_to_qlib.py --source db --timeframes 15min 60min
```

**Advantages:**
- ✅ Automatic funding rate merging
- ✅ Better data integrity
- ✅ Supports incremental updates
- ✅ Works with 8-hour funding rate optimization

**Disadvantages:**
- ❌ Can't recover historical data from 2020
- ❌ Only works for newly collected data

---

### Solution 2: Add Funding Rates to Existing CSV Files

**Best for:** Enriching recent CSV files (<3 months old)

**Prerequisite:** Funding rates must exist in database

1. **Check if funding rates are in database:**

```bash
PGPASSWORD=crypto psql -U crypto_user -h localhost -d qlib_crypto -c \
  "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM funding_rates WHERE symbol='ETHUSDT';"
```

2. **If no funding rates, collect them first:**

```bash
# Ensure market_type is set to "future" or "swap"
# Check config/workflow.json: data.market_type

# Collect funding rates (will go back ~3 months from OKX API)
python scripts/data_service.py run-once
```

3. **Merge funding rates into CSV files:**

```bash
# Dry run to preview
python scripts/add_funding_to_csv.py --symbol ETHUSDT --dry-run

# Actually update CSV files
python scripts/add_funding_to_csv.py --symbol ETHUSDT
```

4. **Reconvert to Qlib format:**

```bash
python scripts/convert_to_qlib.py --source csv --timeframes 15min 60min
```

**Advantages:**
- ✅ Works with existing CSV files
- ✅ Can update files retrospectively (if funding rates were collected)

**Disadvantages:**
- ❌ Limited by OKX API's 3-month historical data window
- ❌ Can't backfill 2020 data
- ❌ Requires manual re-processing

---

### Solution 3: Use Alternative Data Sources (Advanced)

**Best for:** Long-term historical backtesting (2020 and earlier)

**Options:**

1. **Binance API** (may have longer history)
2. **Paid data providers** (CryptoCompare, Kaiko, etc.)
3. **Historical data archives** (if available)

**Implementation:**

You would need to:
1. Obtain historical funding rate data (CSV or API)
2. Import into PostgreSQL `funding_rates` table
3. Run `add_funding_to_csv.py` or use database conversion

---

## Quick Diagnosis

Run this to check your data situation:

```bash
# Check CSV files age
ls -lh data/klines/ETHUSDT/ | head

# Check if funding rates exist in database
python scripts/test_funding_rate_merge.py

# Check configuration
grep -E "output|data_source|use_db" config/workflow.json
```

## Recommendations by Use Case

### For Live Trading / Recent Backtesting (< 3 months)

1. ✅ **Use database storage** (`output: db`, `data_source: db`)
2. ✅ **Enable funding rate collection** (`enable_funding_rate: auto`)
3. ✅ **Run data service continuously**
4. ✅ **8-hour collection optimization** (already implemented)

### For Historical Backtesting (2020-2023)

1. ⚠️ **Accept that funding rates may not be available** for old data
2. ⚠️ **Either:** Skip funding rate features for historical periods
3. ⚠️ **Or:** Obtain historical funding rate data from alternative sources
4. ✅ **Focus on collecting good data going forward**

### For Feature Engineering Without Funding Rates

If funding rates aren't critical to your strategy:

1. Modify handler to not require funding rates
2. Use `CryptoAlpha158` instead of `CryptoAlpha158WithFunding`
3. Or set funding_rate features to 0 and let model learn to ignore them

## Summary

**Why funding_rate is 0.0:**
- CSV files don't have funding_rate column
- Data is from 2020 (before your collection started)
- OKX API can't provide 2020 funding rates

**Fix for new data:**
- Use database storage (`output: db`, `data_source: db`)
- Enable funding rate collection
- Convert from database (now properly merges funding rates)

**Fix for recent CSV files:**
- Collect funding rates if not already in database
- Run `add_funding_to_csv.py` to merge into CSV files
- Reconvert to Qlib format

**For 2020 data:**
- Historical funding rates not available from OKX
- Need alternative data source or proceed without funding rates
