# Tasks for Feature: Crypto Trading Workflow Pipeline

## Summary
Feature dir: /home/watson/work/qlib/features/crypto-workflow  
Primary user stories (derived):  
- US1: Data collection from OKX via ccxt (P1)  
- US2: Training with LightGBM and model persistence (P1)  
- US3: Prediction & signal generation using saved model (P1)  
- US4: Backtest harness and reporting (P2)

## Phase 1 — Setup (project initialization)
- [X] T001 Create directories for data, models, features, signals, backtest, reports (/home/watson/work/qlib)  
- [ ] T002 [P] Add manifest template file /home/watson/work/qlib/features/crypto-workflow/manifest_template.yaml  
- [ ] T003 Create examples script stubs: /home/watson/work/qlib/examples/collect_okx_ohlcv.py, /home/watson/work/qlib/examples/preprocess_features.py, /home/watson/work/qlib/examples/train_lgb.py, /home/watson/work/qlib/examples/predict_and_signal.py, /home/watson/work/qlib/examples/backtest.py
- [ ] T004 Add quickstart and README update: /home/watson/work/qlib/features/crypto-workflow/quickstart.md

## Phase 2 — Foundational (blocking prerequisites)
- [ ] T005 [US1] Implement ccxt-based collector skeleton in /home/watson/work/qlib/examples/collect_okx_ohlcv.py
- [ ] T006 Implement Parquet write utility in /home/watson/work/qlib/utils/io.py
- [ ] T007 Implement basic data validation utilities in /home/watson/work/qlib/features/crypto-workflow/validation.py
- [ ] T008 [US2] Add LightGBM training utility wrapper in /home/watson/work/qlib/features/crypto-workflow/train_utils.py
- [ ] T009 Add model persistence helper in /home/watson/work/qlib/features/crypto-workflow/model_io.py

## Phase 3 — User Stories (priority order)

### US1 (P1): Data collection from OKX via ccxt
- [ ] T010 [US1] Implement full data collector: /home/watson/work/qlib/examples/collect_okx_ohlcv.py (fetch_ohlcv, pagination, rate-limit handling, write parquet)
- [ ] T011 [US1] Implement manifest writer: /home/watson/work/qlib/features/crypto-workflow/manifest.py (write metadata per file)
- [ ] T012 [US1] Add unit test for collector (small mocked fetch) in /home/watson/work/qlib/tests/test_collect_okx.py

### US2 (P1): Train model with LightGBM and persist
- [ ] T013 [US2] Implement preprocessing & feature export: /home/watson/work/qlib/examples/preprocess_features.py (align, fill, featurize, save features parquet)
- [ ] T014 [US2] Implement training entrypoint: /home/watson/work/qlib/examples/train_lgb.py (load features, train LightGBM via LGBModel wrapper, save model to /home/watson/work/qlib/models/)
- [ ] T015 [US2] Output training report generator: /home/watson/work/qlib/features/crypto-workflow/reports/train_report.py
- [ ] T016 [US2] Add unit test verifying model file existence and basic metrics in /home/watson/work/qlib/tests/test_train_lgb.py

### US3 (P1): Load model, predict and generate signals
- [ ] T017 [US3] Implement predictor that loads model and creates signals: /home/watson/work/qlib/examples/predict_and_signal.py
- [ ] T018 [US3] Implement signal rules module: /home/watson/work/qlib/features/crypto-workflow/signal_rules.py (convert scores → BUY/SELL/HOLD, position_size)
- [ ] T019 [US3] Add integration test to run a short predict → signal flow in /home/watson/work/qlib/tests/test_predict_signal.py

### US4 (P2): Backtest harness and reporting
- [ ] T020 [US4] Implement backtest harness: /home/watson/work/qlib/examples/backtest.py (ingest signals + OHLCV, apply slippage/fees, compute metrics)
- [ ] T021 [US4] Implement backtest report serializer: /home/watson/work/qlib/features/crypto-workflow/backtest_report.py
- [ ] T022 [US4] Add backtest smoke test (run with small synthetic data) in /home/watson/work/qlib/tests/test_backtest.py

## Final Phase — Polish & Cross-cutting concerns
- [ ] T023 Update quickstart.md with concrete example commands: /home/watson/work/qlib/features/crypto-workflow/quickstart.md
- [ ] T024 Add basic CI job snippet to run tests and format checks: .github/workflows/feature-crypto-workflow.yml
- [ ] T025 [P] Document assumptions and configuration defaults in /home/watson/work/qlib/features/crypto-workflow/config_defaults.md

## TDD — Tests for each development task (ensure TDD for all implementation work)

- [X] T026 Verify directories created and permissions in /home/watson/work/qlib/tests/test_setup_dirs.py
- [X] T027 [P] Validate manifest template exists and YAML schema in /home/watson/work/qlib/tests/test_manifest_template.py
- [X] T028 [P] Ensure example script stubs importable and exit cleanly in /home/watson/work/qlib/tests/test_examples_stubs.py
- [X] T029 Validate quickstart.md contains required example commands in /home/watson/work/qlib/tests/test_quickstart_examples.py

- [X] T030 [US1] Unit test for ccxt-based collector skeleton behaviors (rate-limit handling stub) in /home/watson/work/qlib/tests/test_collector_skeleton.py
- [X] T031 Unit test for Parquet write utility (round-trip write/read) in /home/watson/work/qlib/tests/test_io_parquet.py
- [X] T032 Unit test for data validation utilities (bad rows flagged) in /home/watson/work/qlib/tests/test_validation.py
- [X] T033 [US2] Unit test for LightGBM training wrapper interface (mock train) in /home/watson/work/qlib/tests/test_train_utils.py
- [X] T034 Unit test for model persistence helper(save/load) in /home/watson/work/qlib/tests/test_model_io.py

- [X] T035 [US1] Unit test for manifest writer ensuring metadata fields present in /home/watson/work/qlib/tests/test_manifest_writer.py
- [X] T036 [US2] Unit test for preprocessing & feature export (no NaNs after featurize) in /home/watson/work/qlib/tests/test_preprocess_features.py
- [X] T037 [US2] Integration/unit test for training entrypoint producing expected model file path in /home/watson/work/qlib/tests/test_train_lgb_entry.py
- [X] T038 [US2] Unit test for training report generator producing JSON/HTML report in /home/watson/work/qlib/tests/test_train_report.py

- [X] T039 [US3] Unit test for signal rules converting scores → BUY/SELL/HOLD and position sizing in /home/watson/work/qlib/tests/test_signal_rules.py
- [X] T040 [US4] Unit test for backtest report serializer (report fields and metrics validity) in /home/watson/work/qlib/tests/test_backtest_report.py

- [X] T041 Validate quickstart examples execute as smoke runs (dry-run) in /home/watson/work/qlib/tests/test_quickstart_smoke.py
- [X] T042 [P] Validate CI workflow file presence and basic syntax in .github/workflows/ (test: /home/watson/work/qlib/tests/test_ci_workflow_presence.py)
- [X] T043 Validate config_defaults.md presence and required keys in /home/watson/work/qlib/tests/test_config_defaults.py

## Dependencies (execution order / gating)
1. Complete Phase 1 tasks T001–T004 before Phase 2.  
2. Phase 2 (T005–T009) must be completed before corresponding user story tasks that depend on utilities.  
3. US1 tasks (T010–T012) are prerequisite for US2 and US3 for real data; synthetic-data tests can run earlier.  
4. US2 (T013–T016) must finish before US3 model-load tasks (T017).  
5. Backtest (T020–T022) depends on US3 signals (T017–T019) and raw OHLCV (T010).

## Parallel execution opportunities
- T002, T003, T004 are parallelizable [P] with each other.
- Implementing utils (T006, T007, T009) can be parallelized where they touch separate files [P].
- Unit tests (T012, T016, T019, T022) can be added in parallel with feature implementation once stubs exist [P].

