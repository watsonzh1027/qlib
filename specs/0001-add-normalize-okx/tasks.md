# Tasks: Add Normalize Function to OKX Data Collector

**Input**: Design documents from `/specs/001-add-normalize-okx/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Following TDD principles from constitution, unit and integration tests are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Status**: ✅ ALL TASKS COMPLETED (14/14) - Feature ready for production

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `scripts/`, `tests/` at repository root
- Paths adjusted based on plan.md structure for data collection script

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Verify qlib environment and pandas dependency availability

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Review existing okx_data_collector.py structure and save_klines function
- [x] T003 Confirm data collection workflow and CSV storage format

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Data Collection with Automatic Normalization (Priority: P1) 🎯 MVP

**Goal**: Enable automatic normalization of kline data during collection process

**Independent Test**: Run data collection script and verify saved CSV files contain properly normalized data (sorted timestamps, no duplicates, correct datetime format)

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Unit test for normalize_klines function in tests/unit/test_okx_normalization.py
- [x] T005 [P] [US1] Integration test for data collection with normalization in tests/integration/test_data_collection_normalization.py

### Implementation for User Story 1

- [x] T006 [US1] Implement normalize_klines function in scripts/okx_data_collector.py
- [x] T007 [US1] Integrate normalization into save_klines function in scripts/okx_data_collector.py
- [x] T008 [US1] Add error handling for timestamp conversion failures in scripts/okx_data_collector.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Empty Data Handling (Priority: P2)

**Goal**: Ensure normalization handles empty data gracefully without errors

**Independent Test**: Run data collection for symbols with no available data and verify no crashes, empty DataFrames handled properly

### Tests for User Story 2 ⚠️

- [x] T009 [P] [US2] Test empty DataFrame normalization in tests/unit/test_okx_normalization.py

### Implementation for User Story 2

- [x] T010 [US2] Verify empty DataFrame handling in normalize_klines function in scripts/okx_data_collector.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T011 [P] Update documentation for normalization feature in docs/
- [x] T012 Code cleanup and ensure consistent error logging in scripts/okx_data_collector.py
- [x] T013 [P] Run quickstart validation per quickstart.md
- [x] T014 Validate test coverage meets >=70% requirement

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 implementation but should be independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD requirement)
- Function implementation before integration
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for normalize_klines function in tests/unit/test_okx_normalization.py"
Task: "Integration test for data collection with normalization in tests/integration/test_data_collection_normalization.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD requirement)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence