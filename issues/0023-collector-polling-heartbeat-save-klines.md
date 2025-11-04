# 0023 - Collector: polling fallback, heartbeat, and save_klines entries support

Status: CLOSED  
Created: 2025-11-03  
Author: automated-report

## Summary
Finalized fixes to the OKX data collector to handle environments without ccxtpro and to ensure on-demand REST updates persist even when the websocket buffer is empty. Added visible heartbeats and graceful shutdown to avoid the process appearing stuck.

## Root cause
- Running without ccxtpro caused the collector to either:
  - Instantiate a ccxt fallback exchange that raises NotSupported when websocket methods are called, or
  - Enter polling mode but show no visible output and never persisted REST-fetched data because save_klines only used the in-memory klines buffer (which remained empty).
- Tests previously masked this because they injected a test shim or monkeypatched ccxtpro.okx.

## Fixes applied
- Removed in-production test placeholder for `ccxtpro.okx`.
- Resolve exchange factories at runtime with importlib.import_module("ccxtpro") / importlib.import_module("ccxt").
- Record `factory_source` and, if not from `ccxtpro`, immediately run a REST-polling fallback instead of attempting websocket calls.
- Polling:
  - Runs as an asyncio background task.
  - Executes update_latest_data via asyncio.to_thread to avoid blocking.
  - Uses an asyncio.Event (`stop_event`) triggered by SIGINT/SIGTERM for graceful shutdown.
  - Polling interval configurable via POLL_INTERVAL (default 60s).
- Heartbeat:
  - Added periodic heartbeat logs for polling and websocket modes so the process emits visible status messages.
- save_klines:
  - Accepts optional `entries` parameter; when provided, saves those rows directly (used by update_latest_data).
  - When no `entries` provided, retains original behavior (use module-level klines buffer and clear it after saving).
- Websocket path:
  - Verify capabilities (`exchange.has` or callable checks) and convert NotSupported exceptions into clear RuntimeError messages if encountered.
- Tests:
  - Tests updated to inject deterministic test shims into `sys.modules` where required.
  - Existing unit tests remain green (user verified).

## Update Log (chronological)
- Detected ccxt/ccxtpro runtime mismatch causing NotSupported or silent polling.
- Implemented runtime importlib resolution for exchange factories.
- Implemented `factory_source`-based decision: ccxtpro -> websocket mode; else -> polling fallback.
- Implemented polling as background task + asyncio.to_thread(update_latest_data).
- Added heartbeat tasks for both modes.
- Modified save_klines to accept explicit entries; updated update_latest_data to pass entries.
- Normalized indentation and fixed prior indentation errors.
- Added signal handling and graceful shutdown logic.
- Verified locally and via unit tests; user confirmed the problem is fixed.

## Verification steps performed
- Unit tests: `pytest tests/test_collector.py --cov=scripts.okx_data_collector` — all relevant tests passed.
- Manual run (no ccxtpro installed): `POLL_INTERVAL=5 python scripts/okx_data_collector.py` — observed heartbeat logs and periodic REST polling logs.
- Shutdown via Ctrl+C resulted in buffered data saving and exchange.close() attempted.

## Outcome
- The collector no longer crashes or appears stuck when ccxtpro is absent.
- REST on-demand updates persist to Parquet even when the websocket buffer is empty.
- Process emits periodic heartbeats for visibility and supports graceful shutdown.

## Next steps / Recommendations
- Consider adding a small CLI or config to choose mode explicitly (polling vs websocket) for operational clarity.
- Add a short README note about POLL_INTERVAL and required runtime dependency (ccxtpro) for websocket mode.
- Optionally add integration tests that run a short-duration polling loop (POLL_INTERVAL low) to ensure end-to-end REST persistence.

Status: CLOSED
