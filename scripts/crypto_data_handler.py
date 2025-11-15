import pandas as pd
import numpy as np
from qlib.data.dataset.handler import DataHandlerLP
from qlib.data.dataset.loader import DataLoaderDH


class CryptoDataHandler(DataHandlerLP):
    """Custom data handler for crypto data with basic technical indicators."""

    def __init__(self, start_time=None, end_time=None, freq="15min", instruments=None, **kwargs):
        # Create data loader
        data_loader = {
            "class": "DataLoaderDH",
            "kwargs": {},
        }

        # Initialize with basic configuration
        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=data_loader,
            infer_processors=[],
            learn_processors=[],
        )
        self.freq = freq  # Store frequency for later use

    def get_feature_config(self):
        """Override to provide basic crypto features."""
        return [
            # Basic price features
            "open", "high", "low", "close", "volume",

            # Simple technical indicators
            "close_ma_5",    # 5-period moving average
            "close_ma_10",   # 10-period moving average
            "close_ma_20",   # 20-period moving average
            "volume_ma_5",   # 5-period volume moving average
            "returns",       # Price returns
            "returns_vol",   # Return volatility (rolling std)
            "high_low_ratio", # High/Low ratio
            "close_open_ratio", # Close/Open ratio
        ]

    def get_label_config(self):
        """Override to use simple price return as label."""
        return ["Ref($close, -1)/$close - 1"], ["LABEL"]

    def _calculate_technical_indicators(self, df):
        """Calculate basic technical indicators for crypto data."""
        # Price-based indicators
        df['close_ma_5'] = df['close'].rolling(window=5).mean()
        df['close_ma_10'] = df['close'].rolling(window=10).mean()
        df['close_ma_20'] = df['close'].rolling(window=20).mean()

        # Volume-based indicators
        df['volume_ma_5'] = df['volume'].rolling(window=5).mean()

        # Return-based indicators
        df['returns'] = df['close'].pct_change()
        df['returns_vol'] = df['returns'].rolling(window=10).std()

        # Ratio indicators
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']

        # Fill NaN values with forward/backward fill, then 0
        df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)

        return df

    def get_all_data(self):
        """Override to add custom technical indicators."""
        # Get basic data from parent class
        df = super().get_all_data()

        if df is not None and not df.empty:
            # Add our custom technical indicators
            df = self._calculate_technical_indicators(df)

        return df