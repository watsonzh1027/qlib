# Data Model: Multi-Portfolio Dataset Split

**Date**: November 19, 2025
**Feature**: 0006-multi-portfolio-dataset-split

## Overview

This feature extends Qlib's dataset handling to support proportion-based segmentation and data volume validation for multi-currency portfolios.

## Entities

### Dataset Configuration
**Purpose**: Configuration object for dataset creation and validation.

**Fields**:
- `class`: String (required) - Dataset class name, e.g., "DatasetH"
- `module_path`: String (required) - Import path, e.g., "qlib.data.dataset"
- `kwargs`: Object (required)
  - `handler`: Reference to data handler config
  - `segments`: Object (required) - Either date ranges or proportions
- `dataset_validation`: Object (optional)
  - `minimum_samples`: Integer (default: 1000) - Minimum training samples required
  - `warning_samples`: Integer (default: 5000) - Warning threshold for training samples

**Validation Rules**:
- `segments` must contain "train", may contain "valid" and "test"
- If proportions used, values must be positive integers
- `dataset_validation` thresholds must be positive integers if specified

**Relationships**:
- References Data Handler Configuration
- Contains Split Points (calculated)

### Symbol Data Range
**Purpose**: Represents the available time range for each cryptocurrency symbol.

**Fields**:
- `symbol`: String (required) - Trading pair identifier, e.g., "BTCUSDT"
- `start_date`: DateTime (required) - Earliest available data point
- `end_date`: DateTime (required) - Latest available data point
- `total_points`: Integer (required) - Total number of data points

**Validation Rules**:
- `start_date` < `end_date`
- `total_points` > 0

**Relationships**:
- Referenced by Split Points calculation

### Split Points
**Purpose**: Calculated timestamp boundaries for train/valid/test segments.

**Fields**:
- `symbol`: String (required) - Associated symbol
- `train_start`: DateTime (optional) - Training period start
- `train_end`: DateTime (required) - Training period end
- `valid_start`: DateTime (optional) - Validation period start
- `valid_end`: DateTime (optional) - Validation period end
- `test_start`: DateTime (optional) - Test period start
- `test_end`: DateTime (optional) - Test period end

**Validation Rules**:
- Time ranges must not overlap
- Time ranges must be sequential
- At least training range must be defined

**Relationships**:
- Calculated from Symbol Data Range and Dataset Configuration

### Dataset Validation Configuration
**Purpose**: Configuration for data quality checks.

**Fields**:
- `minimum_samples`: Integer (default: 1000) - Hard failure threshold
- `warning_samples`: Integer (default: 5000) - Warning threshold

**Validation Rules**:
- `minimum_samples` < `warning_samples` (if both specified)
- Values must be positive integers

**Relationships**:
- Part of Dataset Configuration

## Data Flow

1. **Configuration Loading**: Dataset Configuration loaded from workflow.json
2. **Data Discovery**: Symbol Data Ranges determined from available data
3. **Proportion Calculation**: If proportions specified, convert to date ranges using Symbol Data Ranges
4. **Split Points Generation**: Calculate timestamp boundaries for each segment
5. **Validation**: Check total training samples against thresholds
6. **Dataset Creation**: Initialize Qlib DatasetH with calculated segments

## State Transitions

- **Draft**: Configuration defined but not validated
- **Validated**: Thresholds checked, segments calculated
- **Failed**: Validation failed due to insufficient data
- **Ready**: Dataset successfully created with valid segments