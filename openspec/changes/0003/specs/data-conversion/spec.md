# Spec: data-conversion

## MODIFIED Requirements

### Requirement: Data Conversion Process SHALL
The `convert_to_qlib` module SHALL convert CSV OHLCV data to Qlib binary format instead of Parquet.

#### Scenario: Successful Conversion
Given CSV files in `data/klines` with 15m interval data,
When `convert_to_qlib` is executed,
Then binary files (.bin) are created in `data/qlib_data/crypto` with instruments and features (no calendars needed for crypto trading).

#### Scenario: Dynamic Freq from Interval
Given OHLCV data with interval column,
When freq matches the interval,
Then use the interval column value (e.g., "15m") as the freq parameter for accurate file naming.

#### Scenario: Data Validation
Given invalid CSV data (e.g., missing timestamps),
When conversion is attempted,
Then validation fails and logs an error without creating bin files.

### Requirement: Configuration Usage SHALL
The module SHALL use `workflow.json` for directory paths and parameters.

#### Scenario: Config Loading
Given `workflow.json` specifies `bin_data_dir`,
When module loads config,
Then output directory is set to `data/qlib_data/crypto`.

### Requirement: Binary Format Compatibility SHALL
Converted data SHALL be compatible with Qlib's data loading.

#### Scenario: Qlib Integration
Given converted bin data,
When loaded by Qlib,
Then data is accessible for backtesting without errors.