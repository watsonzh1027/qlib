Status: CLOSED
Created: 2026-02-09 00:05:00
Closed: 2026-02-09 16:06:00

# Problem Description
CSV 记录中出现大量 funding_rate 为 0 的行，怀疑填充逻辑/时间窗口不正确，导致在 8 小时资金费率结算间隔内无法匹配到最近一次 funding 事件。

# Solution
扩大 funding rate 拉取的有效窗口，确保 merge_asof 能匹配到最近一次资金费率事件：
- 增加 lookback（默认 12 小时，可由 config 覆盖）。
- 当 end_time 接近 start_time 时，将 since 回退到 end_time - lookback。
- 对 funding rate 结果按 end_time 窗口过滤，保留最近一条事件用于回填。

# Crucial Update Log
- 2026-02-09 00:05:00: 记录问题：1m 级别窗口太短，fetch_funding_rate_history 返回为空，导致 funding_rate 被填 0。
- 2026-02-09 00:06:00: 修改 okx_data_collector 的 funding rate 获取逻辑，加入 lookback 回退与 end_time 过滤。
- 2026-02-09 00:12:00: 将 lookback 改为复用 data_service 配置（funding_rate_native_interval + funding_collection_window_end），不再依赖 data_collection.funding_rate_lookback_hours。
- 2026-02-09 00:20:00: 新增 CSV 数据 funding_rate 回填函数与命令行开关，支持已下载数据的补全。
- 2026-02-09 00:28:00: 修复回填逻辑与 funding rate 拉取窗口，确保包含区间起点之前的最近结算事件，避免区间内出现 0 值。

# Final Notes
等待用户验证 CSV 中 funding_rate 0 的比例是否显著降低。
