# Implementation Plan: Add Normalize Function to OKX Data Collector

**Branch**: `001-add-normalize-okx` | **Date**: 2025-11-08 | **Spec**: specs/001-add-normalize-okx/spec.md
**Input**: Feature specification from `/specs/001-add-normalize-okx/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a `normalize_klines` function to `okx_data_collector.py` that normalizes downloaded kline data by sorting timestamps, removing duplicates, and ensuring proper datetime formatting, following the pattern established in `collector.py`. The normalization is integrated into the data saving process to ensure data consistency and quality.

## Technical Context

**Language/Version**: Python 3.x (existing codebase)  
**Primary Dependencies**: pandas (for DataFrame operations), existing qlib dependencies  
**Storage**: CSV files in `data/klines/{symbol}/` directory  
**Testing**: pytest (following project TDD standards)  
**Target Platform**: Linux server environment  
**Project Type**: Single data collection script (modifying existing CLI tool)  
**Performance Goals**: Normalization should add minimal overhead (<10% increase in processing time)  
**Constraints**: Must handle large datasets efficiently, preserve data integrity, maintain backward compatibility  
**Scale/Scope**: Support multiple cryptocurrency symbols with 15-minute interval kline data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- TDD Compliance: All new features must follow Red-Green-Refactor cycle with unit and integration tests.
- Test Coverage: Ensure project maintains >=70% overall test coverage.
- Spec-Driven Development: Feature must align with SDD principles for quality and completeness.

## Project Structure

### Documentation (this feature)

```text
specs/001-add-normalize-okx/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
scripts/
└── okx_data_collector.py    # Main script to modify (add normalize_klines function)

tests/
├── unit/                    # Unit tests for normalize_klines function
└── integration/             # Integration tests for data collection with normalization
```

**Structure Decision**: This is a single script modification within the existing data collection module. The feature adds one new function and modifies the existing save_klines function. No new directories or major structural changes are required.

## Phase 0: Outline & Research

### Research Tasks
- **Normalization Pattern Analysis**: Review `collector.py` normalize_crypto method to understand the exact normalization steps and adapt them for kline data
- **Data Format Verification**: Confirm the kline data structure (columns: symbol, timestamp, open, high, low, close, volume, interval)
- **Performance Impact Assessment**: Evaluate the computational cost of normalization on typical dataset sizes
- **Edge Case Handling**: Identify how to handle empty DataFrames, invalid timestamps, and duplicate data

### Research Findings
- **Decision**: Use pandas DataFrame operations for normalization (set_index, drop_duplicates, sort_values)
- **Rationale**: Consistent with existing codebase patterns in collector.py, efficient for tabular data
- **Alternatives Considered**: Custom sorting algorithms (rejected due to complexity), database-level normalization (rejected due to file-based storage)

## Phase 1: Design & Contracts

### Data Model Design
- **KlineRecord Entity**: 
  - Fields: symbol (str), timestamp (datetime), open (float), high (float), low (float), close (float), volume (float), interval (str)
  - Validation: timestamp must be valid datetime, numeric fields must be non-negative
  - Relationships: None (flat structure)

### API Contracts
- **normalize_klines(df: pd.DataFrame) -> pd.DataFrame**
  - Input: DataFrame with kline data
  - Output: Normalized DataFrame
  - Behavior: Sorts by timestamp, removes duplicates, ensures datetime format
  - Error Handling: Returns empty DataFrame unchanged, logs warnings for conversion issues

### Quick Start Guide
1. Activate qlib environment: `conda activate qlib`
2. Run data collection: `python scripts/okx_data_collector.py --start_time 2025-01-01T00:00:00Z --end_time 2025-01-02T00:00:00Z`
3. Check normalized data in `data/klines/{symbol}/{symbol}.csv`
4. Verify data is sorted and deduplicated

### Agent Context Update
Updated Copilot context with:
- normalize_klines function signature and behavior
- Data normalization patterns for financial time series
- Integration points in data collection pipeline

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
