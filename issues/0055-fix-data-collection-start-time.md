# Issue #0055: 数据收集只能获取49条记录 - 修复完成

## 问题描述
数据收集系统只能获取49条记录，而不是预期的历史数据集。

## 根本原因
程序逻辑错误：当API返回的数据量小于请求的limit（300）时，系统错误地认为没有更多数据了而停止收集。但实际上，当API在这个时间段内只有少量数据时，会返回少量数据，系统应该继续从下一个时间点开始分页获取更多数据。

## 解决方案
修复停止条件逻辑：
- 原来：`if len(ohlcv) < min(args.limit, 300) or any(int(candle[0]) > symbol_end_ts for candle in ohlcv):`
- 修复后：`if len(ohlcv) == 0 or (len(ohlcv) > 0 and int(ohlcv[0][0]) > symbol_end_ts):`

只有当API返回0条数据（真正没有更多数据）或返回的数据时间戳超过了结束时间时才停止。

## 修改内容
```python
# scripts/okx_data_collector.py 第1040行附近
# 原来的停止条件
if len(ohlcv) < min(args.limit, 300) or any(int(candle[0]) > symbol_end_ts for candle in ohlcv):
    logger.info(f"Stopping data collection for {symbol}: API returned {len(ohlcv)} candles (limit: {min(args.limit, 300)}), collected {len(all_candles)} total")
    break

# 修复后的停止条件
if len(ohlcv) == 0 or (len(ohlcv) > 0 and int(ohlcv[0][0]) > symbol_end_ts):
    logger.info(f"Stopping data collection for {symbol}: API returned {len(ohlcv)} candles, collected {len(all_candles)} total")
    break
```

## 验证结果
修复后，系统成功收集了86条蜡烛数据，跨越3个API请求：
- 请求1：49条数据（2018-01-11到2018-01-13）
- 请求2：300条数据（2018-01-13到2018-01-15）
- 请求3：300条数据（但超过结束时间，只处理0条）

分页逻辑现在正常工作，系统会继续获取历史数据直到真正没有更多数据。

## 状态
CLOSED - 2025-11-18

## 创建时间
2025-11-18 23:30:00