Status: OPEN
Created: 2026-02-09 22:05:00

# Problem Description
运行 data_service 后 qlib_data 只生成 OHLCV 5 个特征，缺少 vwap 和 funding_rate。原因是 CSV 转换器仅支持层级目录结构，当前 data/klines 采用扁平结构（data/klines/ETHUSDT/ETHUSDT_1m.csv），导致 CSV 源数据未被转换，历史输出沿用旧版本仅含 5 特征。

# Solution
扩展 convert_to_qlib 的 CSV 解析逻辑，兼容扁平目录结构，确保 CSV 中的 vwap/funding_rate 列进入转换流程。

# Crucial Update Log
- 2026-02-09 22:05:00: 记录问题与原因定位（CSV 目录结构不匹配）。
- 2026-02-09 22:06:00: 修改 convert_to_qlib 支持扁平目录结构。
- 2026-02-09 22:09:00: 修复 funding_rate 重采样时重复索引导致的报错（去重并排序索引）。
- 2026-02-10 08:40:00: 转换脚本支持 data_convertor.provider_uri 作为输出目录来源，避免输出路径误解。
- 2026-02-10 08:46:30: 解析 provider_uri 中的 <data.bin_data_dir> 占位符，避免输出目录写成占位符字符串。
- 2026-02-10 08:50:00: 修复 CSV-only 转换路径 mode 未定义导致的 UnboundLocalError。

# Final Notes
需要重新运行 convert_to_qlib 或 data_service 触发转换以生成新增特征文件。
