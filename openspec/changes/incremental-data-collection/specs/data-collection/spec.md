# Data Collection Capability

## MODIFIED Requirements

### Requirement: Incremental Data Fetching
The system SHALL check for existing data files before fetching new data and adjust the fetch window to avoid redundant requests.

#### Scenario: Existing Data Detection
Given a symbol with existing CSV data ending at timestamp T
When data collection is requested for time range [S, E]
Then the system reads T from the file and adjusts start time to max(S, T - overlap)

#### Scenario: Overlap Configuration
Given configurable overlap window of N minutes
When adjusting fetch start time
Then start time is set to T - N minutes to ensure data continuity

#### Scenario: No Existing Data
Given no existing CSV file for a symbol
When data collection is requested
Then full requested time range is fetched as before

#### Scenario: Data Integrity Validation
Given fetched data overlaps with existing data
When merging datasets
Then duplicate timestamps are removed keeping the most recent data

### Requirement: Network Traffic Optimization
The system SHALL minimize API calls by only fetching data outside existing ranges.

#### Scenario: Skip Unnecessary Fetches
Given existing data covers the entire requested range
When collection is triggered
Then no API calls are made for that symbol

#### Scenario: Partial Range Fetching
Given existing data covers [S, M] and request is [S, E] where M < E
When collection executes
Then only data from [M - overlap, E] is fetched