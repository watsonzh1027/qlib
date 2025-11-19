# Tasks: Convert Database to Qlib Format

**Input**: Design documents from `/specs/0005-convert-db-to-qlib/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md

**Tests**: Following TDD principles, tests are included for validation and regression prevention.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Main script: `scripts/convert_to_qlib.py`
- Tests: `tests/test_convert_to_qlib.py`
- Dependencies: Add to `requirements.txt`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup

- [x] T001 Install PostgreSQL adapter dependency (psycopg2-binary) in requirements.txt
- [x] T002 [P] Verify existing Qlib environment and dependencies
- [x] T003 [P] Create test database configuration for development

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database connectivity infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create PostgreSQLStorage class in scripts/convert_to_qlib.py for database connectivity
- [x] T005 Implement database connection management with error handling in PostgreSQLStorage
- [x] T006 Add database query methods for kline data extraction by symbol and timeframe
- [x] T007 Implement data validation for database schema compatibility
- [x] T008 Create unit tests for PostgreSQLStorage class in tests/test_convert_to_qlib.py

**Checkpoint**: Database connectivity ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Convert Database Data to Qlib (Priority: P1) 🎯 MVP

**Goal**: Enable conversion of PostgreSQL-stored kline data to Qlib binary format

**Independent Test**: Run conversion script on database data and verify Qlib can load converted binary files

### Tests for User Story 1 ⚠️

- [x] T009 [P] [US1] Unit test for database data extraction in tests/test_convert_to_qlib.py
- [x] T010 [P] [US1] Integration test for end-to-end database conversion in tests/test_convert_to_qlib.py

### Implementation for User Story 1

- [x] T011 [US1] Extend convert_to_qlib() function to accept database source parameter in scripts/convert_to_qlib.py
- [x] T012 [US1] Integrate PostgreSQLStorage with existing DumpDataCrypto conversion pipeline
- [x] T013 [US1] Add data integrity validation for database-sourced data
- [x] T014 [US1] Implement detailed conversion report output with symbols, time range, record count, and statistics
- [x] T015 [US1] Add command-line options for database connection parameters

**Checkpoint**: At this point, User Story 1 should be fully functional - users can convert database data to Qlib format with detailed reporting

---

## Phase 4: User Story 2 - Flexible Data Source Selection (Priority: P2)

**Goal**: Allow users to choose between CSV, database, or combined data sources

**Independent Test**: Run conversion with different source options and verify correct data loading from each source

### Tests for User Story 2 ⚠️

- [x] T016 [P] [US2] Unit test for data source selection logic in tests/test_convert_to_qlib.py
- [x] T017 [P] [US2] Integration test for multi-source data merging in tests/test_convert_to_qlib.py

### Implementation for User Story 2

- [x] T018 [US2] Add command-line argument parsing for data source selection (--source csv|db|both) in scripts/convert_to_qlib.py
- [x] T019 [US2] Implement data source detection and loading logic
- [x] T020 [US2] Add data deduplication logic for overlapping CSV and database data
- [x] T021 [US2] Update conversion report to show source-specific statistics
- [x] T022 [US2] Ensure backward compatibility with existing CSV-only usage

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - flexible data source selection with deduplication

---

## Phase 5: User Story 3 - Batch Processing and Performance (Priority: P3)

**Goal**: Efficient processing of large datasets with progress tracking and error handling

**Independent Test**: Process large datasets and verify completion within time limits with proper progress reporting

### Tests for User Story 3 ⚠️

- [x] T023 [P] [US3] Performance test for large dataset processing in tests/test_convert_to_qlib.py
- [x] T024 [P] [US3] Error handling test for database connection failures in tests/test_convert_to_qlib.py

### Implementation for User Story 3

- [x] T025 [US3] Implement batch processing for large datasets to manage memory usage
- [x] T026 [US3] Add progress tracking with percentage completion and ETA display
- [x] T027 [US3] Enhance error handling for database connection issues with retry logic
- [x] T028 [US3] Implement partial result preservation when errors occur
- [x] T029 [US3] Add performance optimizations for database queries and data processing

**Checkpoint**: All user stories should now be independently functional with production-ready performance and error handling

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final touches, documentation, and production readiness

- [x] T030 Update script documentation and usage examples in scripts/convert_to_qlib.py docstrings
- [x] T031 Create database setup and configuration documentation
- [x] T032 Add comprehensive error messages and user guidance
- [x] T033 Performance testing with production-scale data (10k+ records)
- [x] T034 Final integration testing across all user stories
- [x] T035 Update project changelog with new database conversion capability

---

## Dependencies & Parallel Execution

### Story Dependencies
- **US1** (P1): Independent - can be implemented first
- **US2** (P2): Depends on US1 completion for data source integration
- **US3** (P3): Can run in parallel with US2 after US1 foundation

### Parallel Opportunities
- [P] Database setup tasks (T001-T003) can run in parallel
- [P] Test creation for each user story can be done in parallel
- [P] Documentation tasks (T030-T031) can run in parallel with final testing

### Implementation Strategy
**MVP Scope**: User Story 1 (database conversion) - delivers core value immediately
**Incremental Delivery**: Each user story adds independent value while maintaining backward compatibility
**Risk Mitigation**: Comprehensive testing ensures no regression in existing CSV functionality

## Success Metrics Alignment

- **FR-001 through FR-011**: All functional requirements covered across user stories
- **SC-001 through SC-007**: All success criteria validated through testing tasks
- **Performance Goals**: Met through US3 batch processing implementation
- **Quality Standards**: TDD approach with comprehensive test coverage</content>
<parameter name="filePath">/home/watson/work/qlib-crypto/specs/0005-convert-db-to-qlib/tasks.md