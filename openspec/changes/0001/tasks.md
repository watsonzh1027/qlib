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

- [ ] Implement `scripts/convert_to_qlib.py`
- [ ] Generate instruments registry
- [ ] Test Qlib data loading
- [ ] Validate data integrity (no gaps, correct timestamps)
- [ ] Run sample backtest strategy
- [ ] Integrate on-demand update with Qlib data provider

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

## File Structure Setup

- [ ] Create `scripts/` directory
- [ ] Create `config/` directory
- [ ] Create `tests/` directory
- [ ] Create `systemd/` directory
- [ ] Create `okx_data/` directory structure
- [ ] Create `qlib_data/` directory structure

---

## Dependencies

- [x] Update `requirements.txt` with new packages
- [ ] Test package installations in qlib environment

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

---

**Completion Criteria**:
- All tasks checked off
- Unit tests pass
- Integration tests pass
- Performance benchmarks met
- Documentation updated
