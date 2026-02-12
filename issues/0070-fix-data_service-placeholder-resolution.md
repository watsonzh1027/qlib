Status: OPEN
Created: 2026-02-09 21:55:00

# Problem Description
okx_data_collector 运行时报错：invalid literal for int() with base 10: '<data_collection.interval'。原因是 data_service 直接读取 data_service.base_interval 等占位符字符串并传给采集器，未做解析。

# Solution
在 DataServiceConfig 中增加占位符解析：
- <data_collection.interval> -> data_collection.interval
- <data.symbols> -> data.symbols
确保传给采集器的参数为实际值。

# Crucial Update Log
- 2026-02-09 21:55:00: 记录问题与原因定位。
- 2026-02-09 21:56:00: 在 data_service 中增加占位符解析，修复 base_interval/symbols 使用。

# Final Notes
等待用户确认采集流程不再出现该错误。
