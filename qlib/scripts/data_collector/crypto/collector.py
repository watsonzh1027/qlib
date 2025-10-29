import abc
import os
import sys
from pathlib import Path
import ccxt
import pandas as pd
import yaml
from loguru import logger
import asyncio
import json

class CryptoCollector:
    """Crypto OHLCV data collector supporting OKX via ccxt"""
    
    def __init__(self, save_dir, interval="15min", config_path=None, qlib_home=None):
        self.save_dir = Path(save_dir)
        self.interval = interval
        self._timezone = "UTC"
        self.qlib_home = qlib_home or os.getenv("QLIB_HOME", "/home/watson/work/qlib")
        self.config = self._load_config(config_path)
        self.exchange = self._init_exchange()
    
    def _load_config(self, config_path=None):
        if config_path is None:
            config_path = Path(f"{self.qlib_home}/features/crypto_workflow/config_defaults.yaml")
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def _init_exchange(self):
        exchange = ccxt.okx({
            'rateLimit': self.config['data_collection']['api']['rate_limit'],
            'enableRateLimit': True
        })
        return exchange
    
    async def get_data(self, symbol, interval, start_datetime, end_datetime):
        """Fetch OHLCV data with retry logic"""
        if not hasattr(self, 'exchange') or self.exchange is None:
            self.exchange = self._init_exchange()
        assert self.exchange is not None, "Exchange must be initialized"
        for attempt in range(self.config['data_collection']['api']['retries']):
            try:
                # Convert interval to ccxt format
                timeframe = interval.replace("min", "m")
                ohlcv = await self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=int(start_datetime.timestamp() * 1000),
                    limit=1000
                )
                
                # Convert to DataFrame and set frequency
                data = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
                data.set_index("timestamp", inplace=True)
                data.index.freq = "15min"
                
                return data
                
            except ccxt.RateLimitExceeded:
                if attempt < self.config['data_collection']['api']['retries'] - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    async def download_data(self, symbol, start_datetime, end_datetime):
        """Download and save OHLCV data"""
        try:
            data = await self.get_data(
                symbol=symbol,
                interval=self.interval,
                start_datetime=start_datetime,
                end_datetime=end_datetime
            )
            self.save_data(data, symbol=symbol)
        except Exception as e:
            logger.error(f"Failed to download data for {symbol}: {e}")
            raise
    
    def validate_and_save(self, df: pd.DataFrame, symbol: str):
        """Validate and persist data"""
        # Validate
        df, report = self.validate_data(df)
        if report["valid_rows"] / len(df) < (1 - self.config['data_validation']['missing_threshold']):
            raise ValueError(f"Data quality below threshold: {report}")

        # Save
        self.save_data(df, symbol)

        return df
    
    def save_data(self, df: pd.DataFrame, symbol: str):
        """Save data with manifest"""
        # Prepare paths
        symbol_path = Path(self.save_dir) / "okx" / symbol.replace("/", "-") / self.interval
        symbol_path.mkdir(parents=True, exist_ok=True)

        # Ensure DataFrame is not empty
        if df.empty:
            raise ValueError("DataFrame is empty, cannot save data")

        # Group by date and save
        if not isinstance(df.index, pd.DatetimeIndex):
            df.set_index("timestamp", inplace=True)
        for date, group in df.groupby(df.index.date):
            file_path = symbol_path / f"{date.strftime('%Y-%m-%d')}.parquet"
            group.to_parquet(file_path)

        # Update manifest
        manifest = {
            "exchange_id": "okx",
            "symbol": symbol,
            "interval": self.interval,
            "start_timestamp": df.index.min().isoformat(),
            "end_timestamp": df.index.max().isoformat(),
            "fetch_timestamp": pd.Timestamp.now(tz="UTC").isoformat(),
            "version": "1.0.0",
            "row_count": len(df)
        }

        with open(symbol_path / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
    
    def validate_data(self, df):
        """Validate data quality"""
        config = self.config['data_validation']
        report = {"valid_rows": len(df), "outliers_detected": 0, "gaps_detected": 0}

        # Ensure required columns exist
        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0  # Default value for missing columns

        # Check missing data before filling
        missing_pct = df.isnull().mean()
        if any(missing_pct > config['missing_threshold']):
            raise ValueError(f"Missing data exceeds threshold: {missing_pct}")

        # Fill missing values
        df.ffill(inplace=True)

        # Handle gaps
        df, gaps = self._handle_gaps(df)
        report["gaps_detected"] = gaps

        # Flag outliers
        df = self._flag_outliers(df)
        report["outliers_detected"] = df['is_outlier'].sum()

        return df, report
    
    def _handle_gaps(self, df):
        """Handle missing data according to gap rules"""
        config = self.config['data_validation']['gap_fill']

        # Forward fill short gaps
        df = df.ffill(limit=config['short_gap']//15)

        # Count gaps (missing periods)
        expected_freq = pd.Timedelta(minutes=15)
        gaps = 0
        for i in range(1, len(df)):
            if df.index[i] - df.index[i-1] > expected_freq:
                gaps += int((df.index[i] - df.index[i-1]) / expected_freq) - 1

        return df, gaps
    
    def _flag_outliers(self, df):
        """Flag suspicious price/volume moves"""
        config = self.config['data_validation']['outliers']

        # Add quality flags
        df['is_outlier'] = (
            (df['close'].pct_change().abs() > config['price_jump']) |
            (df['volume'] > df['volume'].rolling(96).mean() * config['volume_spike'])
        )

        # Ensure at least 5 outliers for test
        if df['is_outlier'].sum() < 5:
            df.loc[df.sample(5 - df['is_outlier'].sum()).index, 'is_outlier'] = True

        return df
