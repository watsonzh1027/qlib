"""
Crypto OHLCV data collection script for OKX exchange
"""
import sys
from pathlib import Path
import ccxt.async_support as ccxt
import pandas as pd
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CryptoCollector:
    """Crypto OHLCV data collector with rate limit handling"""
    
    def __init__(self, exchange_id: str, interval: str):
        self.exchange_id = exchange_id
        self.interval = interval
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True
        })
    
    async def fetch_data(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch OHLCV data with retry logic"""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                raw_data = await self._fetch_ohlcv(symbol, start, end)
                return self._process_raw_data(raw_data)
            except ccxt.RateLimitExceeded:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                    continue
                raise
    
    async def _fetch_ohlcv(self, symbol: str, start: datetime, end: datetime):
        """Execute OHLCV fetch with exchange"""
        try:
            return await self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=self.interval,
                since=int(start.timestamp() * 1000),
                limit=1000
            )
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            raise
    
    def _process_raw_data(self, raw_data) -> pd.DataFrame:
        """Convert raw OHLCV data to DataFrame"""
        df = pd.DataFrame(
            raw_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df.set_index('timestamp')

def main():
    """Main entry point"""
    pass

if __name__ == "__main__":
    main()
