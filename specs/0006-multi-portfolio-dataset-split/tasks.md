# Tasks: Multi-Portfolio Dataset Split

**Input**: Design documents from `/specs/0006-multi-portfolio-dataset-split/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks included per TDD requirements in constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure with qlib/, scripts/, config/, tests/ at repository root

## Dependencies

- User Story 1 is independent and can be implemented after foundational setup
- No inter-story dependencies identified

## Parallel Execution Opportunities

- Unit tests can run in parallel
- Configuration updates can be parallel with code changes
- Integration tests depend on implementation completion

## Implementation Strategy

**MVP Scope**: User Story 1 (proportion-based dataset splitting) - delivers core functionality for fair multi-asset data segmentation.

**Incremental Delivery**: Single user story allows for complete, independently testable feature delivery.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment preparation and dependency verification

- [X] T001 Activate qlib environment and verify Python 3.x availability
- [X] T002 Verify PostgreSQL database connection and crypto data availability
- [X] T003 Confirm required packages installed (qlib, pandas, numpy, pytest)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configuration updates that MUST be complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create backup of existing config/workflow.json
- [X] T005 Add dataset_validation section to config/workflow.json with default thresholds
- [X] T006 Update dataset.segments in config/workflow.json to support proportion integers

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Configure Dataset Splits by Proportion (Priority: P1) 🎯 MVP

**Goal**: Enable data scientists to configure dataset segments using proportions (e.g., 7:2:1) instead of fixed dates, ensuring fair splitting across multi-currency portfolios with varying data ranges.

**Independent Test**: Configure workflow.json with proportion-based segments, run data conversion and training workflow, verify that each symbol's data is split according to specified proportions regardless of individual date ranges, and validate data volume thresholds are enforced.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (TDD Red phase)**

- [X] T007 [P] [US1] Write unit tests for proportion calculation logic in tests/unit/test_proportion_split.py
- [X] T008 [P] [US1] Write unit tests for data volume validation in tests/unit/test_data_validation.py
- [X] T009 [P] [US1] Write integration test for end-to-end proportion splitting workflow in tests/integration/test_dataset_split.py

### Implementation for User Story 1

- [X] T010 [US1] Extend DatasetH class in qlib/data/dataset.py to accept and validate proportion-based segments
- [X] T011 [US1] Implement proportion-to-date conversion logic in scripts/convert_to_qlib.py
- [X] T012 [US1] Add data volume validation calls in scripts/workflow_crypto.py before training
- [X] T013 [US1] Implement error handling for insufficient data scenarios in scripts/workflow_crypto.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Quality assurance, documentation, and final validation

- [X] T014 Update inline code documentation for new proportion handling features
- [X] T015 Run full test suite and verify >=70% coverage maintained
- [X] T016 Test backward compatibility with existing date-based segment configurations
- [X] T017 Update examples/workflow_crypto.py with proportion configuration example
- [X] T018 Validate feature against all success criteria from spec.md</content>
<parameter name="filePath">/home/watson/work/qlib-crypto/specs/0006-multi-portfolio-dataset-split/tasks.md