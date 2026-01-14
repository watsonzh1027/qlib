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
    exchange_name: str = "binance",
    start_date: str = "2024-01-01",
    end_date: str = "2025-01-01",
    output_dir: str = "data/funding_rates"
):
    """
    从指定交易所获取历史资金费率数据
    
    Args:
        symbol: 交易对符号，格式为 "BTC/USDT:USDT" (永续合约)
        exchange_name: 交易所名称 ('binance' 或 'okx')
        start_date: 开始日期，格式 "YYYY-MM-DD"
        end_date: 结束日期，格式 "YYYY-MM-DD"
        output_dir: 输出目录
    
    Returns:
        pd.DataFrame: 包含资金费率历史数据的 DataFrame
    """
    
    # 初始化交易所
    if exchange_name.lower() == 'binance':
        exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    elif exchange_name.lower() == 'okx':
        exchange = ccxt.okx({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
    else:
        raise ValueError(f"不支持的交易所: {exchange_name}")
    
    # 转换日期为时间戳（毫秒）
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000) + 86400000 # 加一天涵盖全天
    
    all_funding_rates = []
    
    print(f"开始从 {exchange_name} 获取 {symbol} 的资金费率数据...")
    print(f"时间范围: {start_date} 至 {end_date}")
    
    if exchange_name.lower() == 'binance':
        # Binance 获取逻辑：支持 since 参数，按时间正序获取
        current_ts = start_ts
        while current_ts < end_ts:
            try:
                # fetch_funding_rate_history(symbol, since, limit)
                batch = exchange.fetch_funding_rate_history(symbol, since=current_ts, limit=1000)
                
                if not batch:
                    break
                    
                # 过滤超出结束时间的数据
                batch = [x for x in batch if x['timestamp'] <= end_ts]
                if not batch:
                    break
                    
                for fr in batch:
                    all_funding_rates.append({
                        'timestamp': fr['timestamp'],
                        'datetime': fr['datetime'],
                        'symbol': fr['symbol'],
                        'funding_rate': float(fr['fundingRate']),
                        'funding_datetime': fr.get('fundingTime', None)
                    })
                
                # 更新时间戳
                last_ts = batch[-1]['timestamp']
                current_ts = last_ts + 1 if last_ts >= current_ts else current_ts + 1
                
                print(f"已获取 {len(all_funding_rates)} 条记录，最新时间: {batch[-1]['datetime']}")
                
                # 如果最后一条数据已经接近或超过结束时间
                if batch[-1]['timestamp'] >= end_ts:
                    break
                    
                time.sleep(exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"Binance 获取出错: {e}")
                break
                
    elif exchange_name.lower() == 'okx':
        # OKX 获取逻辑：需要特殊处理，这里使用 CCXT 的标准方法
        # 注意：OKX API 仅返回最近的数据，如果需要完整历史需用 REST API 脚本逻辑
        # 这里为了保持脚本简洁，使用 CCXT 标准逻辑，但提示用户限制
        print("⚠️ 注意: OKX API 可能仅返回最近3个月的数据。如需更长历史，请使用 binance。")
        
        # OKX通常需要倒序或者有变种，但CCXT统一了接口。
        # 我们尝试使用标准的 fetch_funding_rate_history
        # 如果 CCXT 实现了分页，它会自动处理，否则可能只返回最近100条
        
        # 尝试标准获取（可能受限于 API）
        current_ts = start_ts
        first_run = True
        
        while current_ts < end_ts:
            try:
                funding_rates = exchange.fetch_funding_rate_history(symbol, since=current_ts, limit=100)
                
                if not funding_rates:
                    break
                    
                # 检查是否真的获取到了指定时间的数据
                if first_run and funding_rates[0]['timestamp'] > current_ts + 86400000 * 30: # 差距超过30天
                     print(f"⚠️ API 返回的数据起始时间 ({funding_rates[0]['datetime']}) 远晚于请求时间 ({start_date})")
                     print("这是 OKX API 的限制。")
                     first_run = False
                
                new_records = False
                for fr in funding_rates:
                    # 简单去重：检查最后一条记录的时间戳
                    if all_funding_rates and fr['timestamp'] <= all_funding_rates[-1]['timestamp']:
                        continue
                        
                    if fr['timestamp'] > end_ts:
                        continue
                        
                    all_funding_rates.append({
                        'timestamp': fr['timestamp'],
                        'datetime': fr['datetime'],
                        'symbol': fr['symbol'],
                        'funding_rate': float(fr['fundingRate']),
                        'funding_datetime': fr.get('fundingTime', fr.get('fundingDatetime', None))
                    })
                    new_records = True
                
                if not new_records:
                    break
                    
                # 更新时间戳
                current_ts = funding_rates[-1]['timestamp'] + 1
                
                print(f"已获取 {len(all_funding_rates)} 条记录，最新时间: {funding_rates[-1]['datetime']}")
                
                if funding_rates[-1]['timestamp'] >= end_ts:
                    break
                
                time.sleep(exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"OKX 获取出错: {e}")
                break

    # 转换为 DataFrame
    df = pd.DataFrame(all_funding_rates)
    
    if df.empty:
        print("未获取到任何数据")
        return df
    
    # 数据处理
    # 统一格式：timestamp(datetime), datetime(iso), symbol, funding_rate
    # 注意：我们保留原始毫秒时间戳用于排序，但输出时转为 datetime 对象
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 保存到 CSV
    os.makedirs(output_dir, exist_ok=True)
    symbol_clean = symbol.replace('/', '_').replace(':', '_')
    # 文件名格式保持一致，不包含交易所名称以便后续脚本通用，或可选择包含
    # 为了兼容性，我们保持原文件名格式: SYMBOL_funding_rate.csv
    # 但由于可能有多个来源，如果目录相同会覆盖。
    # 既然用户选择了 exchange，我们假设用户想要该 exchange 的数据作为 authoritative source
    output_file = os.path.join(output_dir, f"{symbol_clean}_funding_rate.csv")
    
    # 仅保存需要的列
    cols = ['timestamp', 'datetime', 'symbol', 'funding_rate', 'funding_datetime']
    # 确保列存在
    for c in cols:
        if c not in df.columns:
            df[c] = None
            
    df[cols].to_csv(output_file, index=False)
    
    print(f"\n数据已保存至: {output_file}")
    print(f"总记录数: {len(df)}")
    print(f"时间范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
    print(f"\n数据预览:")
    print(df[cols].head())
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
  # 使用 Binance 获取 ETH 数据 (推荐，历史数据更全)
  python %(prog)s --symbol ETH/USDT:USDT --exchange binance --start 2023-01-01
  
  # 使用 OKX 获取数据 (仅最近3个月)
  python %(prog)s --symbol ETH/USDT:USDT --exchange okx --start 2025-10-01
  
  # 简写
  python %(prog)s -s BTC/USDT:USDT -x binance -b 2020-01-01
        """
    )
    
    parser.add_argument(
        '-s', '--symbol',
        type=str,
        default='ETH/USDT:USDT',
        help='交易对符号，格式: BASE/QUOTE:SETTLE (默认: ETH/USDT:USDT)'
    )
    
    parser.add_argument(
        '-x', '--exchange',
        type=str,
        default='binance',
        choices=['binance', 'okx'],
        help='交易所 (默认: binance)'
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
    print(f"交易所: {args.exchange}")
    print(f"交易对: {args.symbol}")
    print(f"时间范围: {args.start} 至 {args.end}")
    print(f"输出目录: {args.output}")
    print("=" * 80)
    
    # 获取资金费率数据
    df = fetch_funding_rate_history(
        symbol=args.symbol,
        exchange_name=args.exchange,
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
