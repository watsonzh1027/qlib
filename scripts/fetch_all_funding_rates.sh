#!/bin/bash
# 批量获取多个币种的 funding rate 数据
# 用于改善 Qlib 加密货币模型训练效果

# 币种列表（根据需要修改）
SYMBOLS=("ETH" "BTC" "SOL" "BNB" "XRP" "AAVE")

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
echo "输出目录: $OUTPUT_DIR"
echo "=================================="

# 激活环境
echo "正在激活 conda 环境..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate qlib

if [ $? -ne 0 ]; then
    echo "❌ 无法激活 conda 环境 'qlib'"
    echo "请确保已创建 qlib 环境"
    exit 1
fi

echo "✅ 环境激活成功"
echo ""

# 统计变量
SUCCESS_COUNT=0
FAIL_COUNT=0

# 循环获取
for symbol in "${SYMBOLS[@]}"; do
    echo ">>> 正在获取 ${symbol}/USDT:USDT ..."
    
    python scripts/fetch_funding_rates.py \
        --symbol ${symbol}/USDT:USDT \
        --start $START_DATE \
        --end $END_DATE \
        --output $OUTPUT_DIR
    
    if [ $? -eq 0 ]; then
        echo "✅ ${symbol} 完成"
        ((SUCCESS_COUNT++))
    else
        echo "❌ ${symbol} 失败"
        ((FAIL_COUNT++))
    fi
    
    echo ""
    
    # 避免 API 限流
    if [ $symbol != "${SYMBOLS[-1]}" ]; then
        echo "等待 2 秒以避免 API 限流..."
        sleep 2
    fi
done

echo "=================================="
echo "批量获取完成！"
echo "=================================="
echo "成功: $SUCCESS_COUNT 个"
echo "失败: $FAIL_COUNT 个"
echo ""
echo "数据文件列表:"
ls -lh $OUTPUT_DIR/*.csv 2>/dev/null || echo "未找到 CSV 文件"
echo ""
echo "=================================="

# 显示统计信息
if [ $SUCCESS_COUNT -gt 0 ]; then
    echo ""
    echo "数据统计:"
    for symbol in "${SYMBOLS[@]}"; do
        FILE="${OUTPUT_DIR}/${symbol}_USDT_USDT_funding_rate.csv"
        if [ -f "$FILE" ]; then
            LINES=$(wc -l < "$FILE")
            SIZE=$(du -h "$FILE" | cut -f1)
            echo "  ${symbol}: ${LINES} 行, ${SIZE}"
        fi
    done
fi
