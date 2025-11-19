# Data Format Contracts: Multi-Portfolio Dataset Split

**Date**: November 19, 2025
**Feature**: 0006-multi-portfolio-dataset-split

## Configuration Schema

### Dataset Configuration Contract

**Purpose**: Defines the structure for dataset configuration in workflow.json

**Schema**:
```json
{
  "dataset": {
    "class": "DatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
      "handler": "<data_handler_config>",
      "segments": {
        "train": "VARIANT_A" | "VARIANT_B",
        "valid": "VARIANT_A" | "VARIANT_B" | null,
        "test": "VARIANT_A" | "VARIANT_B" | null
      }
    },
    "dataset_validation": {
      "minimum_samples": "integer >= 1",
      "warning_samples": "integer >= minimum_samples"
    }
  }
}
```

**Variants**:
- **VARIANT_A (Date-based)**: `["2024-01-01", "2024-06-01"]` - Array of start/end dates
- **VARIANT_B (Proportion-based)**: `7` - Integer representing relative proportion

**Validation Rules**:
- `segments` must contain `train` key
- Proportion values must be positive integers
- `dataset_validation` is optional but recommended

## Data Flow Contracts

### Proportion Calculation Contract

**Input**: 
- Symbol data ranges: `List[Dict[symbol, start_date, end_date, total_points]]`
- Proportion specification: `Dict[train=int, valid=int|None, test=int|None]`

**Output**:
- Date segments: `Dict[train=[start, end], valid=[start, end]|None, test=[start, end]|None]`

**Algorithm**:
1. Calculate total proportion = sum of all specified proportions
2. For each symbol:
   - Calculate segment sizes based on proportions
   - Map sizes to date ranges using available data
   - Ensure no overlap and full coverage

**Error Conditions**:
- Insufficient data for requested proportions → ValidationError
- Invalid proportion values → ConfigurationError

### Data Volume Validation Contract

**Input**:
- Training data: `pandas.DataFrame` or compatible data structure
- Thresholds: `Dict[minimum_samples=int, warning_samples=int]`

**Output**:
- Status: `"ok" | "warning" | "error"`
- Message: `str` (error/warning details)

**Validation Logic**:
- Count total training samples across all instruments
- Compare against thresholds
- Return appropriate status and message

## Error Response Contracts

### Insufficient Data Error
```json
{
  "error": "InsufficientTrainingData",
  "message": "Training dataset contains {actual} samples, minimum required is {minimum}",
  "details": {
    "actual_samples": 850,
    "minimum_samples": 1000,
    "symbols_count": 6
  }
}
```

### Data Warning
```json
{
  "warning": "LowTrainingData",
  "message": "Training dataset contains {actual} samples, recommended minimum is {recommended}",
  "details": {
    "actual_samples": 3200,
    "warning_samples": 5000,
    "can_continue": true
  }
}
```