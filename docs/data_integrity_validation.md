# Data Integrity Validation Feature

## Overview

This document describes the data integrity validation feature implemented in the OKX data collector. The feature automatically checks data continuity before downloading new data and clears corrupted data when integrity issues are detected.

## Features

### 1. Pre-Download Data Integrity Checks
- **CSV Files**: Validates timestamp continuity, detects gaps, duplicates, and coverage issues
- **PostgreSQL Database**: Checks for gaps, duplicates, and data density in stored data
- **Automatic Cleanup**: Removes corrupted data before fresh downloads

### 2. Comprehensive Validation Logic

#### CSV Data Validation (`validate_data_continuity`)
- **Gap Detection**: Identifies timestamp gaps larger than expected intervals
- **Duplicate Detection**: Finds duplicate timestamps
- **Coverage Analysis**: Ensures data density meets minimum thresholds (80% coverage)
- **Interval Support**: Configurable for different timeframes (1m, 15m, etc.)

#### Database Validation (`validate_database_continuity`)
- **Gap Analysis**: Uses SQL window functions to detect timestamp gaps
- **Duplicate Checking**: Identifies duplicate records
- **Coverage Metrics**: Calculates data completeness ratios
- **PostgreSQL Optimized**: Uses database-native functions for performance

## Implementation Details

### Modified Functions

#### `validate_data_continuity(df, interval_minutes=1)`
Enhanced to include:
- Duplicate timestamp detection
- Coverage ratio calculation
- More detailed logging

#### `validate_database_continuity(engine, table_name, symbol, interval_minutes=1)`
New function that:
- Queries database for continuity metrics
- Uses window functions for gap detection
- Handles different database backends

#### `update_latest_data()`
Modified to:
- Check data integrity before processing each symbol
- Clear corrupted data automatically
- Log validation results

## Usage

The feature is automatically enabled in the data collection workflow. No additional configuration is required.

### Validation Thresholds
- **Gap Tolerance**: 2x expected interval (e.g., 2 minutes for 1m data)
- **Coverage Minimum**: 80% of expected data points
- **Duplicate Policy**: Zero tolerance for duplicate timestamps

### Logging
All validation results are logged with appropriate severity levels:
- `INFO`: Successful validation
- `WARNING`: Integrity issues detected
- `ERROR`: Validation failures

## Testing

### Unit Tests
- `test_data_integrity.py`: Tests individual validation functions
- `test_integration.py`: Tests complete workflow integration

### Test Coverage
- Empty data handling
- Single data points
- Continuous data validation
- Gap detection
- Duplicate detection
- Coverage analysis

## Benefits

1. **Data Quality Assurance**: Prevents accumulation of corrupted data
2. **Automatic Recovery**: Self-healing through data clearing and re-download
3. **Performance Optimization**: Avoids processing invalid data
4. **Monitoring**: Comprehensive logging for issue tracking
5. **Flexibility**: Works with both CSV and database storage

## Future Enhancements

- Support for additional database backends
- Configurable validation thresholds
- Data repair algorithms (interpolation)
- Historical data integrity auditing
- Performance metrics collection

## Dependencies

- pandas: Data manipulation and analysis
- SQLAlchemy: Database operations
- PostgreSQL: Advanced SQL features for validation

## Error Handling

The system gracefully handles validation failures:
- Continues processing other symbols if one fails
- Logs detailed error information
- Maintains data collection workflow integrity</content>
<parameter name="filePath">/home/watson/work/qlib-crypto/docs/data_integrity_validation.md