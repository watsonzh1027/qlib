# Tasks for Feature: Crypto Trading Workflow Pipeline

## Summary
Feature dir: /home/watson/work/qlib/features/crypto_workflow  
Primary user stories (derived):  
- US1: Data collection from OKX via ccxt (P1)  
- US2: Training with LightGBM and model persistence (P1)  
- US3: Prediction & signal generation using saved model (P1)  
- US4: Backtest harness and reporting (P2)

## Phase 1 — Setup (project initialization)
- [X] T001 Create directories for data, models, features, signals, backtest, reports (/home/watson/work/qlib)  
- [X] T002 [P] Add manifest template file /home/watson/work/qlib/features/crypto_workflow/manifest_template.yaml  
- [X] T003 Create examples script stubs: /home/watson/work/qlib/examples/collect_okx_ohlcv.py, /home/watson/work/qlib/examples/preprocess_features.py, /home/watson/work/qlib/examples/train_lgb.py, /home/watson/work/qlib/examples/predict_and_signal.py, /home/watson/work/qlib/examples/backtest.py
- [X] T004 Add quickstart and README update: /home/watson/work/qlib/features/crypto_workflow/quickstart.md

## Phase 2 — Foundational (blocking prerequisites)
- [X] T005 [US1] Implement ccxt-based collector skeleton in /home/watson/work/qlib/examples/collect_okx_ohlcv.py
- [X] T006 Implement Parquet write utility in /home/watson/work/qlib/utils/io.py
- [X] T007 Implement basic data validation utilities in /home/watson/work/qlib/features/crypto_workflow/validation.py
- [X] T008 [US2] Add LightGBM training utility wrapper in /home/watson/work/qlib/features/crypto_workflow/train_utils.py
- [X] T009 Add model persistence helper in /home/watson/work/qlib/features/crypto_workflow/model_io.py

## Phase 3 — User Stories (priority order)

### US1 (P1): Data collection from OKX via ccxt
- [ ] T010 [US1] Implement full data collector: /home/watson/work/qlib/examples/collect_okx_ohlcv.py (fetch_ohlcv, pagination, rate-limit handling, write parquet)
- [ ] T011 [US1] Implement manifest writer: /home/watson/work/qlib/features/crypto_workflow/manifest.py (write metadata per file)
- [ ] T012 [US1] Add unit test for collector (small mocked fetch) in /home/watson/work/qlib/tests/test_collect_okx.py

### US2 (P1): Train model with LightGBM and persist
- [X] T013 [US2] Implement preprocessing & feature export: /home/watson/work/qlib/examples/preprocess_features.py (align, fill, featurize, save features parquet)
- [X] T014 [US2] Implement training entrypoint: /home/watson/work/qlib/examples/train_lgb.py (load features, train LightGBM via LGBModel wrapper, save model to /home/watson/work/qlib/models/)
- [X] T015 [US2] Output training report generator: /home/watson/work/qlib/features/crypto_workflow/reports/train_report.py
- [X] T016 [US2] Add unit test verifying model file existence and basic metrics in /home/watson/work/qlib/tests/test_train_lgb.py

### US3 (P1): Load model, predict and generate signals
- [X] T017 [US3] Implement predictor that loads model and creates signals: /home/watson/work/qlib/examples/predict_and_signal.py
- [X] T018 [US3] Implement signal rules module: /home/watson/work/qlib/features/crypto_workflow/signal_rules.py (convert scores → BUY/SELL/HOLD, position_size)
- [ ] T019 [US3] Add integration test to run a short predict → signal flow in /home/watson/work/qlib/tests/test_predict_signal.py

### US4 (P2): Backtest harness and reporting
- [ ] T020 [US4] Implement backtest harness: /home/watson/work/qlib/examples/backtest.py (ingest signals + OHLCV, apply slippage/fees, compute metrics)
- [ ] T021 [US4] Implement backtest report serializer: /home/watson/work/qlib/features/crypto_workflow/backtest_report.py
- [ ] T022 [US4] Add backtest smoke test (run with small synthetic data) in /home/watson/work/qlib/tests/test_backtest.py

## Final Phase — Polish & Cross-cutting concerns
- [ ] T023 Update quickstart.md with concrete example commands: /home/watson/work/qlib/features/crypto_workflow/quickstart.md
- [ ] T024 Add basic CI job snippet to run tests and format checks: .github/workflows/feature-crypto-workflow.yml
- [ ] T025 [P] Document assumptions and configuration defaults in /home/watson/work/qlib/features/crypto_workflow/config_defaults.md

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

## Remaining tasks — expanded into actionable sub-tasks

Note: below each task we add short sub-steps, acceptance criteria (AC) and a rough estimate (hrs).

T008 [US2] Add LightGBM training utility wrapper in /home/watson/work/qlib/features/crypto_workflow/train_utils.py
- Sub-steps:
  - Implement LGBModel wrapper class exposing fit(X,y,params), predict(X), save(path), load(path).
  - Add simple hyperparameter defaults and early-stopping support.
  - Add logging and basic metric computation (AUC / RMSE).
- AC:
  - Unit test can mock train and verify fit/predict/save/load interface.
  - Training returns a dict with metrics.
- Estimate: 8h

T009 Add model persistence helper in /home/watson/work/qlib/features/crypto_workflow/model_io.py
- Sub-steps:
  - Implement save_model(obj, path) and load_model(path) using joblib/pickle with schema metadata file (yaml/json).
  - Ensure atomic write (temp file + rename).
- AC:
  - Round-trip save/load yields same predict results on a small sample.
- Estimate: 3h

T010 [US1] Implement full data collector: /home/watson/work/qlib/examples/collect_okx_ohlcv.py
- Sub-steps:
  - Implement fetch_ohlcv(symbol, since, limit, timeframe) with pagination.
  - Add exponential-backoff for rate-limit errors and retry policy.
  - Convert to pandas.DataFrame and write Parquet via utils.io.
  - Add CLI args for symbol, timeframe, start/end and output path.
- AC:
  - Collector can run in dry-run mode and produce parquet with required columns (ts, open, high, low, close, volume).
- Estimate: 12h

T011 [US1] Implement manifest writer: /home/watson/work/qlib/features/crypto_workflow/manifest.py
- Sub-steps:
  - Build function write_manifest(file_path, metadata_dict) that appends/updates a per-file YAML manifest.
  - Include schema: symbol, timeframe, start_ts, end_ts, row_count, file_hash.
- AC:
  - Manifest file written and validated by test_manifest_writer.
- Estimate: 3h

T012 [US1] Add unit test for collector (small mocked fetch) in /home/watson/work/qlib/tests/test_collect_okx.py
- Sub-steps:
  - Mock ccxt exchange.fetch_ohlcv returning two pages.
  - Assert collector writes parquet and manifest entry.
- AC:
  - Test passes with CI mock mode.
- Estimate: 4h

T013 [US2] Implement preprocessing & feature export: /home/watson/work/qlib/examples/preprocess_features.py
- Sub-steps:
  - Implement align_time_index, forward-fill/back-fill rules, compute basic indicators (MA, RSI).
  - Save processed features to parquet with partitioning by symbol/timeframe.
- AC:
  - No NaNs after featurize for target prediction windows (covered by test_preprocess_features).
- Estimate: 8h

T014 [US2] Implement training entrypoint: /home/watson/work/qlib/examples/train_lgb.py
- Sub-steps:
  - Load features parquet, split train/val/test by time, call LGBModel wrapper to train.
  - Persist model via model_io to /home/watson/work/qlib/models/.
  - Emit a small JSON training report with metrics and hyperparams.
- AC:
  - Model file created and report exists (test_train_lgb_entry).
- Estimate: 6h

T015 [US2] Output training report generator: /home/watson/work/qlib/features/crypto_workflow/reports/train_report.py
- Sub-steps:
  - Implement report generator that accepts metrics dict and writes JSON + basic HTML (template).
- AC:
  - train_report unit test validates existence and basic fields.
- Estimate: 4h

T016 [US2] Add unit test verifying model file existence and basic metrics in /home/watson/work/qlib/tests/test_train_lgb.py
- Sub-steps:
  - Run training entrypoint in dry-run or with tiny dataset, assert model + report files.
- AC:
  - Test must be deterministic and fast.
- Estimate: 3h

T017 [US3] Implement predictor that loads model and creates signals: /home/watson/work/qlib/examples/predict_and_signal.py
- Sub-steps:
  - Load model via model_io, run predict over feature parquet, append timestamped score.
  - Persist signals parquet and call signal_rules to convert to discrete signals.
- AC:
  - Signals parquet contains columns: ts, symbol, score, signal, pos_size.
- Estimate: 6h

T018 [US3] Implement signal rules module: /home/watson/work/qlib/features/crypto_workflow/signal_rules.py
- Sub-steps:
  - Implement thresholds to map score → BUY/SELL/HOLD.
  - Implement simple position sizing (score normalized * max_risk).
  - Expose configurable thresholds via YAML or function args.
- AC:
  - Unit tests translate example scores to expected signals and sizes.
- Estimate: 3h

T019 [US3] Add integration test to run a short predict → signal flow in /home/watson/work/qlib/tests/test_predict_signal.py
- Sub-steps:
  - Use saved model fixture or small synthetic model to run predict_and_signal.
  - Assert signals meet expectations.
- AC:
  - Test covers end-to-end predict + signal rules.
- Estimate: 4h

T020 [US4] Implement backtest harness: /home/watson/work/qlib/examples/backtest.py
- Sub-steps:
  - Ingest signals + OHLCV, simulate fills with slippage/fees, track positions and PnL.
  - Produce basic metrics: cumulative return, max drawdown, sharpe.
- AC:
  - Backtest accepts config and outputs CSV/JSON report.
- Estimate: 12h

T021 [US4] Implement backtest report serializer: /home/watson/work/qlib/features/crypto_workflow/backtest_report.py
- Sub-steps:
  - Serialize metrics + trade list to JSON/HTML.
- AC:
  - test_backtest_report validates fields and types.
- Estimate: 4h

T022 [US4] Add backtest smoke test (run with small synthetic data) in /home/watson/work/qlib/tests/test_backtest.py
- Sub-steps:
  - Create synthetic OHLC and signal series, run backtest, assert non-error and plausible metrics.
- AC:
  - Smoke test executes within CI time budget.
- Estimate: 4h

T023 Update quickstart.md with concrete example commands: /home/watson/work/qlib/features/crypto_workflow/quickstart.md
- Sub-steps:
  - Add example CLI commands for collect→preprocess→train→predict→backtest.
  - Add notes about API keys, dry-run and test mode.
- AC:
  - quickstart smoke tests validate presence of commands (test_quickstart_examples/test_quickstart_smoke).
- Estimate: 2h

T024 Add basic CI job snippet to run tests and format checks: .github/workflows/feature-crypto-workflow.yml
- Sub-steps:
  - Add workflow to run pytest and flake/black on push/PR to feature branch.
- AC:
  - CI workflow file present and syntactically valid (test_ci_workflow_presence).
- Estimate: 2h

T025 [P] Document assumptions and configuration defaults in /home/watson/work/qlib/features/crypto_workflow/config_defaults.md
- Sub-steps:
  - Add default paths, timezones, model naming conventions, and retry settings.
- AC:
  - test_config_defaults validates presence and required keys.
- Estimate: 2h

## Suggested immediate next actions (pick in order)
1. Implement T009 (model_io) and T008 (train_utils) — they unblock T014/T017/T019 and are small.
2. Implement T013 (preprocess) so training can consume realistic features.
3. Implement T014 (train entrypoint) and T016 (train unit test).
4. Implement T018 (signal_rules) and T017 (predict_and_signal).
5. Implement collector T010 and manifest T011 in parallel with tests T012.
6. Implement backtest T020/T021 and T022 last.

## PR guidance
- Create one small PR per logical unit (e.g., model_io, train_utils, preprocess_features).
- Include unit tests with each PR (mock where necessary).
- Use feature branch naming: feature/crypto-workflow/<task-number>-<short-desc>.

## Status tracking
Current Progress: 15/25 tasks completed (60%)
Latest completed:
- T017: Predictor implementation with model loading and signal generation
- T018: Signal rules module for converting scores to trading signals
- T016: Unit test for training implemented (test_train_lgb.py)

## Next immediate actions (updated)
1. Implement T019 (predict → signal integration test)
2. Continue collector work (T010/T011) in parallel with tests T012
3. Implement backtest T020/T021 and T022 after signals are ready

