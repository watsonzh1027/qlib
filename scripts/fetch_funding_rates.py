"""
资金费率数据获取示例

本脚本演示如何从 OKX 获取历史资金费率数据并保存为 CSV 格式。
资金费率是永续合约特有的机制，用于锚定合约价格与现货价格，是重要的市场情绪指标。
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
import os

def fetch_funding_rate_history(
    symbol: str = "BTC/USDT:USDT",
    start_date: str = "2024-01-01",
    end_date: str = "2025-01-01",
    output_dir: str = "data/funding_rates"
):
    """
    从 OKX 获取历史资金费率数据
    
    Args:
        symbol: 交易对符号，格式为 "BTC/USDT:USDT" (永续合约)
        start_date: 开始日期，格式 "YYYY-MM-DD"
        end_date: 结束日期，格式 "YYYY-MM-DD"
        output_dir: 输出目录
    
    Returns:
        pd.DataFrame: 包含资金费率历史数据的 DataFrame
    """
    
    # 初始化 OKX 交易所
    exchange = ccxt.okx({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # 永续合约
        }
    })
    
    # 转换日期为时间戳（毫秒）
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    
    all_funding_rates = []
    current_ts = start_ts
    
    print(f"开始获取 {symbol} 的资金费率数据...")
    print(f"时间范围: {start_date} 至 {end_date}")
    
    while current_ts < end_ts:
        try:
            # OKX API: 获取资金费率历史
            # 参考: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history
            funding_rates = exchange.fetch_funding_rate_history(
                symbol,
                since=current_ts,
                limit=100  # 每次最多获取 100 条
            )
            
            if not funding_rates:
                print(f"未获取到数据，时间戳: {current_ts}")
                break
            
            for fr in funding_rates:
                all_funding_rates.append({
                    'timestamp': fr['timestamp'],
                    'datetime': fr['datetime'],
                    'symbol': fr['symbol'],
                    'funding_rate': fr['fundingRate'],
                    'funding_datetime': fr.get('fundingDatetime', None),
                })
            
            # 更新时间戳到最后一条记录
            current_ts = funding_rates[-1]['timestamp'] + 1
            
            print(f"已获取 {len(all_funding_rates)} 条记录，最新时间: {funding_rates[-1]['datetime']}")
            
            # 避免触发 API 限流
            time.sleep(exchange.rateLimit / 1000)
            
        except Exception as e:
            print(f"获取数据时出错: {e}")
            break
    
    # 转换为 DataFrame
    df = pd.DataFrame(all_funding_rates)
    
    if df.empty:
        print("未获取到任何数据")
        return df
    
    # 数据处理
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['funding_rate'] = df['funding_rate'].astype(float)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # 保存到 CSV
    os.makedirs(output_dir, exist_ok=True)
    symbol_clean = symbol.replace('/', '_').replace(':', '_')
    output_file = os.path.join(output_dir, f"{symbol_clean}_funding_rate.csv")
    df.to_csv(output_file, index=False)
    
    print(f"\n数据已保存至: {output_file}")
    print(f"总记录数: {len(df)}")
    print(f"\n数据预览:")
    print(df.head())
    print(f"\n统计信息:")
    print(df['funding_rate'].describe())
    
    return df


def merge_funding_rate_with_ohlcv(
    ohlcv_file: str,
    funding_rate_file: str,
    output_file: str = None
):
    """
    将资金费率数据与 OHLCV 数据合并
    
    Args:
        ohlcv_file: OHLCV CSV 文件路径
        funding_rate_file: 资金费率 CSV 文件路径
        output_file: 输出文件路径（可选）
    
    Returns:
        pd.DataFrame: 合并后的数据
    """
    
    # 读取数据
    ohlcv = pd.read_csv(ohlcv_file, parse_dates=['datetime'])
    funding = pd.read_csv(funding_rate_file, parse_dates=['timestamp'])
    
    # 重命名列以便合并
    funding = funding.rename(columns={'timestamp': 'datetime'})
    
    # 使用 merge_asof 进行时间对齐（向前填充）
    # 每根 K 线会匹配最近的历史资金费率
    merged = pd.merge_asof(
        ohlcv.sort_values('datetime'),
        funding[['datetime', 'funding_rate']].sort_values('datetime'),
        on='datetime',
        direction='backward'  # 向前查找最近的资金费率
    )
    
    print(f"合并完成:")
    print(f"  OHLCV 记录数: {len(ohlcv)}")
    print(f"  资金费率记录数: {len(funding)}")
    print(f"  合并后记录数: {len(merged)}")
    print(f"  资金费率缺失值: {merged['funding_rate'].isna().sum()}")
    
    if output_file:
        merged.to_csv(output_file, index=False)
        print(f"\n合并数据已保存至: {output_file}")
    
    return merged


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='获取加密货币永续合约的历史资金费率数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 获取 ETH 最近2年的数据
  python %(prog)s --symbol ETH/USDT:USDT --start 2023-01-01 --end 2025-01-15
  
  # 获取 BTC 数据并指定输出目录
  python %(prog)s --symbol BTC/USDT:USDT --start 2022-01-01 --output data/funding_rates
  
  # 获取多个币种（使用循环）
  for symbol in BTC ETH SOL; do
    python %(prog)s --symbol ${symbol}/USDT:USDT --start 2023-01-01
  done
  
  # 使用简写参数
  python %(prog)s -s ETH/USDT:USDT -b 2023-01-01 -e 2025-01-15
        """
    )
    
    parser.add_argument(
        '-s', '--symbol',
        type=str,
        default='ETH/USDT:USDT',
        help='交易对符号，格式: BASE/QUOTE:SETTLE (默认: ETH/USDT:USDT)'
    )
    
    parser.add_argument(
        '-b', '--start',
        type=str,
        default='2023-01-01',
        help='开始日期，格式: YYYY-MM-DD (默认: 2023-01-01)'
    )
    
    parser.add_argument(
        '-e', '--end',
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help='结束日期，格式: YYYY-MM-DD (默认: 今天)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='data/funding_rates',
        help='输出目录路径 (默认: data/funding_rates)'
    )
    
    parser.add_argument(
        '--merge',
        action='store_true',
        help='是否与 OHLCV 数据合并'
    )
    
    parser.add_argument(
        '--ohlcv-file',
        type=str,
        help='OHLCV CSV 文件路径（用于合并）'
    )
    
    parser.add_argument(
        '--merge-output',
        type=str,
        help='合并后的输出文件路径'
    )
    
    args = parser.parse_args()
    
    # 显示配置信息
    print("=" * 80)
    print("资金费率数据获取工具")
    print("=" * 80)
    print(f"交易对: {args.symbol}")
    print(f"时间范围: {args.start} 至 {args.end}")
    print(f"输出目录: {args.output}")
    print("=" * 80)
    
    # 获取资金费率数据
    df = fetch_funding_rate_history(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output
    )
    
    # 如果需要合并数据
    if args.merge and args.ohlcv_file:
        if df.empty:
            print("\n⚠️  资金费率数据为空，无法进行合并")
        else:
            print("\n" + "=" * 80)
            print("开始合并 OHLCV 数据...")
            print("=" * 80)
            
            symbol_clean = args.symbol.replace('/', '_').replace(':', '_')
            funding_file = os.path.join(args.output, f"{symbol_clean}_funding_rate.csv")
            
            merged = merge_funding_rate_with_ohlcv(
                ohlcv_file=args.ohlcv_file,
                funding_rate_file=funding_file,
                output_file=args.merge_output
            )
    
    if not df.empty:
        print("\n" + "=" * 80)
        print("✅ 完成！")
        print("=" * 80)
