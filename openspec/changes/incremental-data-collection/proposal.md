# Proposal: Incremental Data Collection Optimization

## Summary
Modify the data collection process to avoid redundant data fetching by checking existing CSV files and only fetching data outside the current time range, with optional overlap for data integrity.

## Motivation
Current implementation fetches data from start_time to end_time without considering existing data, leading to unnecessary network requests and potential data duplication. This optimization will reduce API calls and improve efficiency.

## Impact
- Reduces network traffic and API usage
- Prevents data duplication
- Maintains data integrity with configurable overlap
- Backward compatible with existing workflows

## Implementation Approach
- Check if CSV file exists for each symbol
- Read the last timestamp from existing file
- Adjust start_time to last_timestamp - overlap_window
- Fetch only new data from adjusted start_time to end_time
- Merge with existing data ensuring no gaps

## Dependencies
- Requires pandas for timestamp parsing
- No new external dependencies

## Testing
- Unit tests for timestamp comparison logic
- Integration tests with mock API responses
- Validation of data continuity after merge