# Design: Incremental Data Collection

## Architecture Overview
The incremental data collection introduces a pre-fetch check phase that analyzes existing data files to determine the optimal fetch window, reducing redundant API calls while maintaining data integrity.

## Key Components

### Existing Data Analyzer
- Reads the last timestamp from existing CSV files
- Calculates overlap window based on configuration
- Adjusts fetch parameters dynamically

### Fetch Window Calculator
- Compares existing data range with requested range
- Determines if fetch is needed
- Computes adjusted start_time with overlap

### Data Merger
- Handles merging new data with existing data
- Ensures timestamp continuity
- Removes duplicates based on timestamp

## Trade-offs

### Performance vs Integrity
- Overlap window ensures data integrity but may refetch some data
- Configurable overlap allows tuning between efficiency and safety

### Complexity vs Benefit
- Added logic increases code complexity
- Significant reduction in API calls for frequent updates

### Backward Compatibility
- Existing behavior preserved when no existing data
- Configuration-driven overlap prevents breaking changes

## Configuration
```json
{
  "data_collection": {
    "overlap_minutes": 15,
    "enable_incremental": true
  }
}
```

## Error Handling
- Graceful fallback to full fetch if file reading fails
- Logging of optimization decisions
- Validation of merged data integrity