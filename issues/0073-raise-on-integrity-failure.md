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

# Update 2026-02-12
## New Problem Report
运行 `python scripts/data_service.py start` 后，转换为 qlib_data 的 instruments/all.txt 只包含少量 symbol（如 5 个），与 config/instruments.json 中完整列表不一致。
初步观察：`convert_to_qlib.py` 的 CSV 路径在做 `validate_data_integrity` 时要求“完整连续时间戳”，一旦存在缺口就会丢弃该 symbol，导致最终 instruments/all.txt 被大幅缩减。
这与 0073 中“完整性校验与异常处理”直接相关，是当前问题的触发因素之一。

## Resolution Plan
1) 诊断与复现
	- 在 `convert_to_qlib.py` 增加日志：记录每个 symbol 是否通过完整性校验、缺口数量与缺口区间（start/end）。
	- 通过 `data_service` 触发一次转换，生成转换报告（symbol -> pass/fail + gap stats）。

2) 规则调整：可配置的完整性策略
	- 移除 `warn`/`skip`（对数据采集无意义，禁止降级质量）。
	- 新增配置项：`data_convertor.integrity_mode`（`strict|renew`），默认 `strict`。
	- `strict`: 遇到缺口直接失败（保持 0073 的“强一致”行为）。
	- `renew`: 发现缺口后删除该 symbol 的历史数据并重新采集（从源头重建连续数据）。

2.1) 采集任务状态记录
	- 采集过程中记录状态（开始时间、结束时间、进度、失败原因、重试次数），以支持断点续跑（resume task）。
	- 状态文件建议与 backfill_state 同目录管理，按 symbol 归档。

3) 符号来源统一
	- `convert_to_qlib.py` 在 CSV 路径下优先读取 `config/instruments.json` 作为“期望 symbols”，
	  并对缺失数据的 symbol 给出明确日志（未找到 CSV/未通过完整性/被跳过原因）。
	- 确保 qlib instruments 使用统一符号格式（如 `ETHUSDT` 或 `ETH_USDT`），避免混用。

4) 测试与验证
	- 新增单元测试：
	  - `integrity_mode=warn` 时，存在缺口的 symbol 仍写入 instruments/all.txt。
	  - `integrity_mode=strict` 时，缺口 symbol 被拒并报错。
	- 回归验证：对比 `config/instruments.json` 与 `data/qlib_data/crypto_15min/instruments/all.txt`，数量与格式符合预期。

5) 文档与操作说明
	- 更新 `docs/data_integrity_validation.md` 说明 `integrity_mode` 的行为与推荐设置。
	- 在 data_service 日志中明确提示当前完整性策略。

## Crucial Update Log (2026-02-12)
- 实施 `data_collection.integrity_mode` 仅支持 `strict|renew`，并在采集阶段引入状态记录（支持 resume）。
- 在 `okx_data_collector` 增加严格失败抛错与 renew 清理重采逻辑。
- 新增测试覆盖 strict/renew 行为与状态文件落地（未运行测试）。
- `convert_to_qlib` CSV 转换改为严格模式：完整性失败或缺失期望 symbols 直接抛错，避免静默丢失。
- 新增转换严格模式与缺失 symbols 的单元测试（未运行测试）。
- `data_service` 启动日志补充完整性策略与 resume 配置。
- 启动 data_service 后，严格模式在 ETHUSDT(1m) 触发完整性失败并中断采集（IntegrityError）。
- 将 `integrity_mode` 切换为 `renew` 并重启 data_service，采集重新开始，collection_state 文件已生成。
- 发现 renew 频繁触发的根因：existing CSV 中存在少量重复时间戳导致完整性失败；增加重复去重路径并限制 renew 次数。
- renew 超限会写入 diagnostics 并输出 critical 日志，抛出 IntegrityError 终止处理。
- gap 情况优先回补缺口，回补失败时记录 missing_ranges 并以 critical 终止，避免反复 renew。
- 修正 collection_state 在成功完成时清理旧的 failure reason/diagnostics，避免状态误读。
- 启用 long backfill 以处理超过 max_gap_backfill_days 的长缺口（当前 ETHUSDT 缺口约 36 天）。
- 修复 backfill_state 中已完成 chunk 但加载 0 行导致的假完成，自动重置并重试该 chunk。
- backfill_state 读取时去重 done_chunks，并记录 chunk_rows，防止重复条目导致回补误判。
- 2026-02-14: 增加 data_service 转换前的数据完整性门槛（基于 start/end 覆盖），并新增单元测试覆盖“完整/不完整时转换跳过”。
- 2026-02-14: convert_to_qlib 增加“resample 后无新增 bar 则跳过 symbol”的过滤，避免无意义的重复转换。
- 2026-02-14: 修复 data_service 转换门槛的 okx_data_collector 导入路径，并修正 convert_to_qlib 在 1min 场景未追加 CSV 的问题；更新相关测试断言。
- 2026-02-14: data_service 转换门槛改为严格 end_time 覆盖（end_tolerance=0），修复测试用例与时区处理错误。
