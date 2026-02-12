Status: OPEN
Created: 2026-02-10 09:02:00

# Problem Description
Qlib 转换时数据完整性校验失败，多个标的缺少时间序列连续性。要求不放宽校验，需要在源头补齐缺失的 OHLCV 时间间隔。

# Solution
在 okx_data_collector 保存阶段新增缺口填充：
- 依据 interval 生成完整时间索引。
- 对缺失行前向填充 close，并将 open/high/low 填为 close，volume=0。
- vwap 使用 close 作为缺失填充值；funding_rate 前向填充。
- 默认启用，可通过 data_collection.fill_missing_intervals 控制。

# Tests
- 新增 test_save_klines_fills_missing_intervals，验证缺口补齐与 volume=0。

# Crucial Update Log
- 2026-02-10 09:02:00: 记录问题与处理方案。
- 2026-02-10 09:03:00: 添加缺口填充与单元测试。
- 2026-02-10 16:00:00: 追加缺口回补逻辑，检测缺失时间段并通过交易所补拉 OHLCV，避免转换阶段因连续性校验失败而丢弃标的。
- 2026-02-10 22:50:00: 增加长时间分段回填（segmented backfill）支持：
  - 新配置项：`data_collection.enable_long_backfill`, `data_collection.backfill_chunk_days`, `data_collection.backfill_state_dir`, `data_collection.backfill_snapshot_dir`。
  - 行为：按分片（默认 90 天）回填、每片写入 CSV、持久化已完成片段状态以支持 resume，并在首片前保存 CSV 快照（gzip）。
  - CLI 支持：`--long-backfill` / `--backfill-chunk-days` / `--resume-backfill`。

# Final Notes
需要重新采集/重写 CSV 后再转换以生效。
