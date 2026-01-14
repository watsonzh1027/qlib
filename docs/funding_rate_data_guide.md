# Funding Rate 数据获取指南

## 📋 脚本功能

`scripts/fetch_funding_rates.py` 是一个灵活的命令行工具，用于从 OKX 交易所获取加密货币永续合约的历史资金费率数据。

## 🚀 快速开始

### 基本用法

```bash
# 激活环境
conda activate qlib

# 获取 ETH 从2023年至今的数据（默认）
python scripts/fetch_funding_rates.py

# 获取 BTC 数据
python scripts/fetch_funding_rates.py --symbol BTC/USDT:USDT

# 指定时间范围
python scripts/fetch_funding_rates.py --symbol ETH/USDT:USDT --start 2022-01-01 --end 2025-01-15
```

## 📝 参数说明

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--symbol` | `-s` | `ETH/USDT:USDT` | 交易对符号 |
| `--start` | `-b` | `2023-01-01` | 开始日期 (YYYY-MM-DD) |
| `--end` | `-e` | 今天 | 结束日期 (YYYY-MM-DD) |
| `--output` | `-o` | `data/funding_rates` | 输出目录 |
| `--merge` | - | False | 是否与 OHLCV 合并 |
| `--ohlcv-file` | - | - | OHLCV 文件路径 |
| `--merge-output` | - | - | 合并后输出路径 |

## 💡 使用示例

### 1. 获取单个币种的长期历史数据

```bash
# 获取 ETH 2年历史数据（约2190条记录）
python scripts/fetch_funding_rates.py \
  --symbol ETH/USDT:USDT \
  --start 2023-01-01 \
  --end 2025-01-15
```

### 2. 批量获取多个币种

```bash
# 方法1：使用 bash 循环
for symbol in BTC ETH SOL BNB; do
  echo "获取 ${symbol} 数据..."
  python scripts/fetch_funding_rates.py \
    --symbol ${symbol}/USDT:USDT \
    --start 2023-01-01
done

# 方法2：创建批处理脚本（见下方）
```

### 3. 使用简写参数

```bash
# 简洁写法
python scripts/fetch_funding_rates.py -s BTC/USDT:USDT -b 2022-01-01 -e 2025-01-15
```

### 4. 与 OHLCV 数据合并

```bash
python scripts/fetch_funding_rates.py \
  --symbol ETH/USDT:USDT \
  --start 2023-01-01 \
  --merge \
  --ohlcv-file data/klines/eth_usdt_4h_future.csv \
  --merge-output data/merged/eth_with_funding.csv
```

## 📊 数据说明

### 输出文件格式

文件名：`{SYMBOL}_funding_rate.csv`
例如：`ETH_USDT_USDT_funding_rate.csv`

CSV 列：
- `timestamp`: 时间戳（datetime 格式）
- `datetime`: ISO 格式日期时间
- `symbol`: 交易对符号
- `funding_rate`: 资金费率（浮点数）
- `funding_datetime`: 资金费率结算时间

### 数据频率

- **OKX 永续合约**：每8小时结算一次
- **每天3次**：00:00, 08:00, 16:00 (UTC)
- **每月约90条记录**
- **每年约1095条记录**

### 时间范围建议

| 用途 | 建议时间范围 | 记录数 |
|------|-------------|--------|
| 模型训练 | 2年+ | 2000+ |
| 回测验证 | 1年+ | 1000+ |
| 快速测试 | 3个月 | 270+ |

## 🔧 批量获取脚本

创建 `scripts/fetch_all_funding_rates.sh`:

```bash
#!/bin/bash
# 批量获取多个币种的 funding rate 数据

# 币种列表
SYMBOLS=("BTC" "ETH" "SOL" "BNB" "XRP" "AAVE")

# 时间范围
START_DATE="2023-01-01"
END_DATE=$(date +%Y-%m-%d)

# 输出目录
OUTPUT_DIR="data/funding_rates"

echo "=================================="
echo "批量获取 Funding Rate 数据"
echo "=================================="
echo "时间范围: $START_DATE 至 $END_DATE"
echo "币种数量: ${#SYMBOLS[@]}"
echo "=================================="

# 激活环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate qlib

# 循环获取
for symbol in "${SYMBOLS[@]}"; do
    echo ""
    echo ">>> 正在获取 ${symbol}/USDT:USDT ..."
    
    python scripts/fetch_funding_rates.py \
        --symbol ${symbol}/USDT:USDT \
        --start $START_DATE \
        --end $END_DATE \
        --output $OUTPUT_DIR
    
    if [ $? -eq 0 ]; then
        echo "✅ ${symbol} 完成"
    else
        echo "❌ ${symbol} 失败"
    fi
    
    # 避免 API 限流
    sleep 2
done

echo ""
echo "=================================="
echo "✅ 全部完成！"
echo "=================================="
echo "数据保存在: $OUTPUT_DIR"
ls -lh $OUTPUT_DIR/*.csv
```

使用方法：
```bash
chmod +x scripts/fetch_all_funding_rates.sh
./scripts/fetch_all_funding_rates.sh
```

## ⚠️ 注意事项

### API 限流
- OKX API 有速率限制
- 脚本内置了延迟机制（`time.sleep`）
- 批量获取时建议间隔2-3秒

### 网络问题
- 需要稳定的网络连接
- 如果中断，可以重新运行（会从上次结束位置继续）
- 建议使用代理（如果在国内）

### 数据完整性
- 获取后检查记录数是否合理
- 检查是否有缺失值
- 验证日期范围是否正确

## 🎯 针对当前项目的建议

### 推荐配置

```bash
# 获取 ETH 2年历史数据用于模型训练
conda activate qlib
python scripts/fetch_funding_rates.py \
  --symbol ETH/USDT:USDT \
  --start 2023-01-01 \
  --end 2025-01-15 \
  --output data/funding_rates
```

**预期结果**：
- 约 2190 条记录（2年 × 365天 × 3次/天）
- 文件大小：约 100-200 KB
- 覆盖完整的训练和测试期间

### 验证数据

```bash
# 查看文件信息
wc -l data/funding_rates/ETH_USDT_USDT_funding_rate.csv

# 查看数据范围
head -2 data/funding_rates/ETH_USDT_USDT_funding_rate.csv
tail -2 data/funding_rates/ETH_USDT_USDT_funding_rate.csv
```

### 更新 workflow 配置

获取数据后，需要更新训练时间范围以匹配 funding rate 数据：

```yaml
data_handler_config:
    start_time: 2023-01-01  # 与 funding rate 开始时间一致
    end_time: 2025-01-15    # 与 funding rate 结束时间一致
    fit_start_time: 2023-01-01
    fit_end_time: 2024-12-31
```

## 📚 相关文档

- [OKX API 文档](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history)
- [CCXT 文档](https://docs.ccxt.com/)
- [Qlib 文档](https://qlib.readthedocs.io/)

## 🐛 故障排除

### 问题1：ModuleNotFoundError: No module named 'ccxt'
```bash
conda activate qlib
pip install ccxt
```

### 问题2：网络连接超时
```bash
# 设置代理（如需要）
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

### 问题3：API 限流错误
- 增加脚本中的 `time.sleep` 延迟
- 减少每次请求的 `limit` 参数
- 分批获取数据

### 问题4：数据不完整
- 检查网络连接
- 重新运行脚本
- 验证日期范围是否在交易所支持范围内
