Status: OPEN
Created: 2026-02-10 09:12:00

# Problem Description
需要在采集/保存阶段进行完整性检查，并在发现缺口时记录详细信息或直接抛出异常，从源头发现与解决问题，而不是事后补齐。

# Solution
在 save_klines 中增加完整性校验与诊断：
- 保存前调用 validate_data_continuity。
- 记录 start/end/expected/actual/coverage 诊断信息。
- 新增开关 data_collection.raise_on_integrity_failure；启用时直接抛 RuntimeError。

# Tests
- 新增 test_save_klines_raise_on_integrity_failure 覆盖异常抛出逻辑。

# Crucial Update Log
- 2026-02-10 09:12:00: 记录问题与方案。
- 2026-02-10 09:13:00: 完成完整性异常抛出与测试。
- 2026-02-10 15:20:00: 修复 save_klines 缩进混用导致的 IndentationError。

# Final Notes
需要用户验证采集阶段是否能及时发现问题并在日志中定位缺口。
