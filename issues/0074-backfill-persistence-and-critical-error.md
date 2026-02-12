Status: CLOSED
Created: 2026-02-12 10:05:00

# Problem Description
在数据采集与保存阶段发现数据连续性缺失时，期望自动尝试 backfill 补齐。若连续 backfill 失败应：
- 将失败状态持久化以便人工介入；
- 抛出可被上层捕获的明确异常以提醒监控与告警。

# Final Solution
- 增加 `BackfillCriticalError`（继承自 `RuntimeError`），在连续 backfill 失败达到阈值时抛出。
- 使用 per-symbol JSON 状态文件在 `data_collection.backfill_state_dir`（默认 `data/backfill_state`）下记录：
  - `done_chunks`: 完成的时间区间列表（用于恢复时跳过）；
  - `last_failure`: 最近失败时间与错误信息；
  - `snapshot_taken`: 是否已对失败期间做过 CSV 快照（默认禁用）。
- 新增配置项：
  - `data_collection.max_consecutive_backfill_failures`（默认 3）
  - `data_collection.enable_backfill_snapshot`（默认 false）
  - `data_collection.backfill_state_dir`, `data_collection.backfill_snapshot_dir`
- 在发生完整性检测失败时，会尝试 `backfill_missing_ranges` 分段补齐（chunk 可配置）。
  - 若 `backfill_missing_ranges` 成功则恢复正常流程。
  - 若重复失败并超过阈值：持久化失败状态并抛出 `BackfillCriticalError`。
- 当输出目标为 Postgres 时，`backfill_missing_ranges` 在标记 chunk 为已完成后会尝试通过 `PostgresStorage.get_ohlcv_data(start_time, end_time)` 恢复该 chunk 的真实行数据以返回给调用方（实现 DB-aware resume）。
- 禁用原来的自动 CSV 快照功能（默认），保留可选的快照功能供诊断使用。
- 统一存储 API 时间参数命名为 `start_time` / `end_time`（并提供短期的别名兼容），并更新相关调用方与测试。

# Tests
- 新增/更新的测试位于 `tests/test_okx_data_collector.py`：
  - `test_backfill_failure_raises_critical`（验证失败时创建文件并抛异常）
  - `test_backfill_resume_loads_from_db_when_target_db`（验证 Postgres 恢复行为）
  - 及大量与 `save_klines`、`validate_data_continuity`、`update_latest_data` 相关的边界情况测试。
- 所有 OKX 采集模块相关测试已通过：`pytest tests/test_okx_data_collector.py` -> 65 passed.

# Crucial Update Log
- 2026-02-10 09:12:00: 记录初始需求与设计草案。
- 2026-02-10 15:45:00: 设计并实现 `BackfillCriticalError` 与 per-symbol backfill state。
- 2026-02-11 11:20:00: 完成 DB-aware resume（PostgresStorage.get_ohlcv_data 恢复 chunk 行）。
- 2026-02-11 15:00:00: 禁用默认快照行为并添加 `data_collection.enable_backfill_snapshot` 配置。
- 2026-02-11 18:00:00: 大量测试修复（时区、CSV append、时间参数命名、边界合并等）。
- 2026-02-12 10:05:00: 关闭 issue（实现完成并进行了模块级测试）。

# Files Changed
- `scripts/okx_data_collector.py` — 主要实现点：`BackfillCriticalError`、状态持久化、`backfill_missing_ranges`、可选 snapshot、增强的 `save_klines` 与 `update_latest_data`。
- `scripts/postgres_storage.py` — `get_ohlcv_data` / `get_funding_rates` 接受 `start_time`/`end_time` 参数。
- `scripts/convert_to_qlib.py` — 兼容性与调用更新。
- `tests/test_okx_data_collector.py` — 新增/更新测试覆盖。
- `config/workflow.json` — 新增默认 `data_collection.enable_backfill_snapshot: false`。

# Notes
- 后续建议：
  - 移除遗留的 `start_date`/`end_date` 参数别名并在文档中写明迁移说明（当前已做短期别名兼容）。
  - 在 CI 中加入模块级与集成级测试以覆盖 DB 恢复路径。
  - Added migration `scripts/migrations/0001_add_created_at_funding_rates.sql` to add `created_at` to `funding_rates` if operators prefer an explicit `created_at` column (safe `IF NOT EXISTS`, and optional backfill commented in file).
