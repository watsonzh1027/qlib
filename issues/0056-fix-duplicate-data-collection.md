# Issue #0056: 重复采集数据问题 - 数据库已有最近数据仍从2018年开始采集

## 问题描述
数据库中已经有最近的数据，但程序仍然从2018-01-01开始重新采集全部历史数据，导致重复采集和性能问题。

## 根本原因
`calculate_fetch_window`函数的逻辑有缺陷：当数据库中有最近的数据时，系统仍然会从请求的开始时间（2018-01-01）重新采集所有数据，而不是只更新最新的数据。

## 解决方案
修改`calculate_fetch_window`函数的逻辑：
- 将数据"新近度"检查从固定的24小时改为基于数据间隔的动态检查
- 计算数据间隔对应的时间间隔（例如1小时间隔对应1小时，1天间隔对应1天）
- 只有在数据库数据存在间隔级别的缺口时才进行数据更新
- 正确处理历史数据补充和最新数据更新

## 修改内容
```python
# scripts/okx_data_collector.py 第427-434行附近
# 原来的逻辑 - 固定24小时检查
data_is_recent = (current_time - last_timestamp) <= pd.Timedelta(hours=24)

# 修改后的逻辑 - 基于间隔的动态检查
interval_minutes = get_interval_minutes(interval)
interval_timedelta = pd.Timedelta(minutes=interval_minutes)
needs_update_start = (first_timestamp - start_time) > interval_timedelta
needs_update_end = (end_time - last_timestamp) > interval_timedelta
```

## 验证结果
修复后，系统正确检测数据缺口并只获取缺失的数据：

### 测试案例1：历史数据补充
```
DEBUG - Symbol BTC/USDT: interval=1h, interval_minutes=60, needs_update_start=True, needs_update_end=False
INFO - Symbol BTC/USDT: Need earlier historical data, fetching from 2018-01-01T00:00:00+00:00
INFO - No new data to add for BTC/USDT (all 494 candles already exist in PostgreSQL)
```

### 测试案例2：最新数据覆盖
```
DEBUG - Symbol BTC/USDT: interval=1h, interval_minutes=60, needs_update_start=False, needs_update_end=False
INFO - Symbol BTC/USDT: Existing data fully covers requested range and is up-to-date, skipping fetch
INFO - Symbol BTC/USDT: Data range 2018-01-11 11:00:00+00:00 to 2025-11-19 07:00:00+00:00, requested 2025-11-18 20:00:00+00:00 to 2025-11-18 22:00:00+00:00
INFO - Skipping BTC/USDT - no new data needed
```

### 测试案例3：未来数据范围
```
DEBUG - Symbol BTC/USDT: interval=1h, interval_minutes=60, needs_update_start=False, needs_update_end=False
INFO - Symbol BTC/USDT: Existing data fully covers requested range and is up-to-date, skipping fetch
INFO - Symbol BTC/USDT: Data range 2018-01-11 11:00:00+00:00 to 2025-11-19 07:00:00+00:00, requested 2025-11-19 00:00:00+00:00 to 2025-11-19 02:00:00+00:00
INFO - Skipping BTC/USDT - no new data needed
```

## 修复总结
- ✅ **智能缺口检测**：基于数据间隔动态计算是否需要更新数据
- ✅ **避免重复采集**：当数据库数据覆盖请求范围时，正确跳过数据获取
- ✅ **历史数据补充**：当存在早期数据缺口时，正确获取缺失的历史数据
- ✅ **最新数据更新**：当存在最新数据缺口时，正确获取新的数据
- ✅ **分页逻辑优化**：正确处理API分页并在时间边界停止

## 状态
CLOSED - 2025-11-19

## 创建时间
2025-11-19 00:10:00

## 最后更新
2025-11-19 00:25:00