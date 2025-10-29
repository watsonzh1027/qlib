#!/usr/bin/env python3
"""
OKX OHLCV data collector with pagination and rate limit handling
"""
import sys
from pathlib import Path
import logging
import time
import ccxt
import pandas as pd
from datetime import datetime, timedelta
import argparse
from typing import List, Dict, Optional
import asyncio

# Add qlib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qlib.utils.io import write_parquet
from features.crypto_workflow.manifest import write_manifest

logger = logging.getLogger(__name__)

class OKXCollector:
    """OKX data collector with rate limiting and pagination"""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.max_retries = 3
        self.retry_delay = 5  # seconds
    
    async def download_data(self, symbol: str, start_datetime: datetime, end_datetime: datetime, output_path: Path) -> None:
        """Download and save OHLCV data"""
        try:
            df = self.collect_historical(
                symbol=symbol,
                timeframe="1h",
                start_time=start_datetime,
                end_time=end_datetime,
                output_path=output_path
            )
            logger.info(f"Successfully downloaded data for {symbol} to {output_path}")
        except Exception as e:
            logger.error(f"Failed to download data for {symbol}: {e}")
            raise
    
    def fetch_ohlcv_with_retry(
        self, 
        symbol: str,
        timeframe: str,
        since: Optional[int] = None,
        limit: int = 100
    ) -> List[List]:
        """Fetch OHLCV data with exponential backoff retry"""
        for attempt in range(self.max_retries):
            try:
                data = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                if isinstance(data, asyncio.Future):
                    data = data.result()
                return data
            except ccxt.RateLimitExceeded:
                if attempt == self.max_retries - 1:
                    raise
                sleep_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, sleeping {sleep_time}s")
                time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Error fetching data: {str(e)}")
                raise
    
    def collect_historical(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        output_path: Path
    ) -> pd.DataFrame:
        """Collect historical data with pagination"""
        all_data = []
        current_time = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        
        iteration = 0
        while current_time < end_ts:
            iteration += 1
            print(f"Iteration {iteration}: current_time={current_time}, end_ts={end_ts}")
            
            batch = self.fetch_ohlcv_with_retry(
                symbol=symbol,
                timeframe=timeframe,
                since=current_time,
                limit=100
            )
            
            if not batch:
                print("No more data received, breaking loop")
                break
                
            all_data.extend(batch)
            current_time = batch[-1][0] + 1  # Next timestamp after last received
            print(f"Collected {len(batch)} candles until {datetime.fromtimestamp(current_time/1000)}")
            
        # Convert to DataFrame
        df = pd.DataFrame(
            all_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Save to parquet
        write_parquet(df, output_path)
        
        # Write manifest
        metadata = {
            'symbol': symbol,
            'timeframe': timeframe,
            'start_ts': start_time.isoformat(),
            'end_ts': end_time.isoformat(),
            'row_count': len(df)
        }
        write_manifest(output_path, metadata)
        
        return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=True, help='Trading pair (e.g. BTC/USDT)')
    parser.add_argument('--timeframe', default='1h', help='Candle timeframe')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', required=True, help='Output parquet file path')
    parser.add_argument('--api-key', help='OKX API key')
    parser.add_argument('--api-secret', help='OKX API secret')
    
    args = parser.parse_args()
    
    collector = OKXCollector(args.api_key, args.api_secret)
    
    start_time = datetime.strptime(args.start, '%Y-%m-%d')
    end_time = datetime.strptime(args.end, '%Y-%m-%d')
    
    collector.collect_historical(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_time=start_time,
        end_time=end_time,
        output_path=Path(args.output)
    )

if __name__ == '__main__':
    main()
