# Tasks for Proposal 0001: Crypto Data Feeder Module

**Status**: IMPLEMENTATION  
**Proposal**: `../proposals/0001-crypto-data-feeder.md`

---

## Phase 1: Core Data Collection (Week 1)

- [x] Implement `scripts/get_top50.py` with OKX API integration (via CCXT)
- [x] Write unit tests for symbol selection logic
- [x] Create `scripts/okx_data_collector.py` with cryptofeed
- [x] Add Parquet storage with proper schema
- [x] Implement `update_latest_data()` method for on-demand fetching
- [x] Test with 5 symbols for 24 hours

**Deliverables**:
- Working data collector with on-demand update
- 24h of sample data
- Basic error handling

---

## Phase 2: Qlib Integration (Week 2)

- [x] Update `scripts/get_top50.py` to generate `config/instruments.json` with metadata.
- [x] Implement `scripts/convert_to_qlib.py` with updated workflow:
  - Scan `data/klines/{symbol}/*.parquet`
  - Merge and deduplicate data by `(symbol, timestamp)`
  - Convert to Qlib binary format and save in `data/qlib_data/`
- [x] Generate instruments registry in Qlib format.
- [x] Test Qlib data loading.
- [x] Validate data integrity (no gaps, correct timestamps).
- [ ] Run sample backtest strategy.
- [ ] Integrate on-demand update with Qlib data provider.

**Deliverables**:
- Qlib-compatible data format
- Sample strategy execution proof
- On-demand update callable from Qlib

---

## Phase 3: Automation & Monitoring (Week 3)

- [ ] Create systemd service files
- [ ] Set up cron jobs for scheduling
- [ ] Add logging framework (Python `logging`)
- [ ] Implement health checks
- [ ] Write runbook for common failures

**Deliverables**:
- Production-ready automation
- Monitoring dashboard (optional)
- Operation documentation

---

## Phase 4: Backtest Integration (Week 3)

- [x] Update `scripts/sample_backtest.py` to use `ConfigManager`.
- [x] Create `config/workflow.json` for centralized parameter storage.
- [ ] Validate end-to-end functionality of the backtest pipeline.

**Deliverables**:
- Centralized parameter management.
- Functional backtest pipeline with crypto data.

---

## Phase 5: Module Rework and Retesting (Week 4)

- [ ] Update `scripts/get_top50.py` to align with the updated data flow.
- [ ] Modify `scripts/okx_data_collector.py` for compatibility with the revised schema.
- [ ] Refactor `scripts/convert_to_qlib.py` to handle new data formats.
- [ ] Revise `scripts/sample_backtest.py` to incorporate centralized parameter management.
- [ ] Conduct unit tests for all modified modules.
- [ ] Perform integration tests to validate end-to-end functionality.

**Deliverables**:
- Updated modules aligned with the new design.
- Comprehensive test results ensuring functionality.

---

## File Structure Setup

- [x] Create `scripts/` directory
- [x] Create `config/` directory
- [x] Create `tests/` directory
- [x] Create `systemd/` directory
- [x] Create `data/` directory structure

---

## Dependencies

- [x] Update `requirements.txt` with new packages
- [x] Test package installations in qlib environment

---

## Documentation

- [ ] Update `README.md` with setup instructions
- [ ] Mark `docs/data_feeder.md` as implemented
- [ ] Create operation runbook

---

## Implementation notes

- [x] Read and will follow `./.github/prompts/openspec-apply.prompt.md` workflow for implementing this change:
  - Follow Steps 1–5 in the prompt (read proposal & tasks → implement tasks sequentially → run tests → update checklist → update issue records).
  - Work focused on one primary problem at a time and append progress to the existing issue file for this proposal.

- [x] Add design.md describing architecture and component responsibilities (`openspec/changes/0001/design.md`)
- [x] Add spec delta for data collection (`openspec/changes/0001/specs/data_collection/spec.md`)
- [x] Run `openspec validate 0001 --strict` and resolve any validation issues.

---

**Completion Criteria**:
- All tasks checked off
- Unit tests pass
- Integration tests pass
- Performance benchmarks met
- Documentation updated
