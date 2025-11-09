# Tasks: 0002-crypto-workflow

**Input**: Design documents from `/specs/0002-crypto-workflow/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included per TDD requirements in constitution (Red-Green-Refactor cycle)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `examples/`, `tests/` at repository root
- **Scripts**: `scripts/` for utilities
- **Config**: `config/` for configuration files

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create examples/workflow_crypto.py with basic structure
- [X] T002 Extend scripts/config_manager.py with workflow-specific methods
- [X] T003 Update config/workflow.json with crypto workflow sections
- [ ] T004 Create tests/test_workflow_crypto.py test file structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Implement ConfigManager.get_workflow_config() in scripts/config_manager.py
- [X] T006 [P] Implement ConfigManager.get_model_config() in scripts/config_manager.py
- [X] T007 [P] Implement ConfigManager.get_trading_config() in scripts/config_manager.py
- [X] T008 Setup data loading verification for data/qlib_data/crypto
- [X] T009 Configure qlib initialization for crypto data provider

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Run Complete Crypto Trading Workflow (Priority: P1) 🎯 MVP

**Goal**: Enable users to execute a complete workflow that loads crypto data, trains a model, generates signals, and performs backtesting

**Independent Test**: Run the workflow script and verify all components complete successfully with valid outputs

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Unit test for data loading in tests/test_workflow_crypto.py
- [ ] T011 [P] [US1] Unit test for model training in tests/test_workflow_crypto.py
- [ ] T012 [P] [US1] Unit test for signal generation in tests/test_workflow_crypto.py
- [ ] T013 [P] [US1] Integration test for complete workflow in tests/test_workflow_crypto.py

### Implementation for User Story 1

- [X] T014 [US1] Implement data loading from qlib crypto provider in examples/workflow_crypto.py
- [X] T015 [US1] Implement model training with GBDT on crypto data in examples/workflow_crypto.py
- [X] T016 [US1] Implement signal generation using trained model in examples/workflow_crypto.py
- [X] T017 [US1] Implement backtesting with crypto-specific parameters in examples/workflow_crypto.py
- [X] T018 [US1] Add experiment logging and recorder setup in examples/workflow_crypto.py
- [X] T019 [US1] Add error handling and validation in examples/workflow_crypto.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Adapt Existing Framework for Crypto (Priority: P2)

**Goal**: Reuse qlib framework structure and adapt it for crypto data instead of traditional stock data

**Independent Test**: Compare workflow structure to original workflow_by_code.py and verify crypto-specific adaptations

### Tests for User Story 2 ⚠️

- [ ] T020 [P] [US2] Unit test for config parameter loading in tests/test_workflow_crypto.py
- [ ] T021 [P] [US2] Integration test for framework adaptation in tests/test_workflow_crypto.py

### Implementation for User Story 2

- [X] T022 [US2] Adapt qlib initialization for crypto data provider in examples/workflow_crypto.py
- [X] T023 [US2] Configure dataset for crypto OHLCV data in examples/workflow_crypto.py
- [X] T024 [US2] Set up backtest executor for 15-minute frequency in examples/workflow_crypto.py
- [X] T025 [US2] Configure trading strategy for crypto instruments in examples/workflow_crypto.py
- [X] T026 [US2] Integrate with existing qlib recorder and analysis in examples/workflow_crypto.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Validate Crypto Model Performance (Priority: P3)

**Goal**: Analyze trained model performance on crypto data through signal analysis and backtesting metrics

**Independent Test**: Examine generated analysis reports and backtest metrics for reasonableness in crypto context

### Tests for User Story 3 ⚠️

- [ ] T027 [P] [US3] Unit test for signal analysis in tests/test_workflow_crypto.py
- [ ] T028 [P] [US3] Unit test for portfolio analysis in tests/test_workflow_crypto.py

### Implementation for User Story 3

- [X] T029 [US3] Implement signal analysis for crypto signals in examples/workflow_crypto.py
- [X] T030 [US3] Implement portfolio analysis for crypto backtesting in examples/workflow_crypto.py
- [X] T031 [US3] Add performance metrics calculation in examples/workflow_crypto.py
- [X] T032 [US3] Generate analysis reports with crypto-appropriate metrics in examples/workflow_crypto.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T033 [P] Documentation updates in docs/ for crypto workflow
- [ ] T034 Code cleanup and refactoring in examples/workflow_crypto.py
- [ ] T035 Performance optimization for 15-minute data processing
- [ ] T036 [P] Additional unit tests in tests/test_workflow_crypto.py
- [ ] T037 Security and error handling improvements
- [ ] T038 Run quickstart.md validation and update if needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 for data but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Data loading before model training
- Model training before signal generation
- Signal generation before backtesting
- Core implementation before analysis

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel
- All tests for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for data loading in tests/test_workflow_crypto.py"
Task: "Unit test for model training in tests/test_workflow_crypto.py"
Task: "Unit test for signal generation in tests/test_workflow_crypto.py"
Task: "Integration test for complete workflow in tests/test_workflow_crypto.py"

# Launch implementation tasks sequentially within story:
Task: "Implement data loading from qlib crypto provider in examples/workflow_crypto.py"
Task: "Implement model training with GBDT on crypto data in examples/workflow_crypto.py"
...
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
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (core workflow)
   - Developer B: User Story 2 (framework adaptation)
   - Developer C: User Story 3 (performance validation)
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