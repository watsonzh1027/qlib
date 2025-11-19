# Quick Start: Multi-Portfolio Dataset Split

**Date**: November 19, 2025
**Feature**: 0006-multi-portfolio-dataset-split

## Overview

This guide shows how to configure proportion-based dataset splitting for multi-currency crypto portfolios in Qlib.

## Prerequisites

- Qlib environment activated
- PostgreSQL database with crypto OHLCV data
- workflow.json configured for your symbols

## Configuration

### 1. Update workflow.json

Add dataset validation and proportion-based segments:

```json
{
  "dataset": {
    "class": "DatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
      "handler": "<data_handler_config>",
      "segments": {
        "train": 7,
        "valid": 2,
        "test": 1
      }
    },
    "dataset_validation": {
      "minimum_samples": 1000,
      "warning_samples": 5000
    }
  }
}
```

### 2. Run Data Conversion

Convert database data to Qlib format:

```bash
cd /path/to/qlib-crypto
conda activate qlib
python scripts/convert_to_qlib.py --source db
```

### 3. Execute Training Workflow

Run the crypto trading workflow:

```bash
python examples/workflow_crypto.py
```

## Expected Behavior

### With Sufficient Data
- Dataset initializes successfully
- Training proceeds normally
- Console shows: "Dataset validation passed: X samples available"

### With Low Data (Warning)
- Dataset initializes with warning
- Training continues
- Console shows: "WARNING: Training data low (X samples < Y recommended)"

### With Insufficient Data (Error)
- Process terminates with error
- Console shows: "ERROR: Insufficient training data (X samples < Y minimum)"
- No training occurs

## Troubleshooting

### Common Issues

**"Proportion values must be positive integers"**
- Check that segment values are integers > 0
- Example: `"train": 7` not `"train": "7"`

**"No data available for symbol"**
- Verify symbol exists in database
- Check date ranges in data collection config

**"Dataset validation failed"**
- Increase data collection period
- Reduce minimum_samples threshold
- Add more symbols to portfolio

### Configuration Examples

**Basic proportions (70/20/10)**:
```json
"segments": {"train": 7, "valid": 2, "test": 1}
```

**Validation only (no proportions)**:
```json
"segments": {"train": ["2024-01-01", "2024-06-01"]},
"dataset_validation": {"minimum_samples": 1000}
```

**High-frequency trading**:
```json
"dataset_validation": {"minimum_samples": 10000, "warning_samples": 50000}
```

## Next Steps

- Monitor training performance with different proportion ratios
- Adjust thresholds based on your model's requirements
- Consider cross-validation for small datasets