import pandas as pd
import numpy as np
import talib
from typing import Dict, List

def generate_features(df: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
    """Generate feature set from OHLCV data"""
    features = pd.DataFrame(index=df.index)
    
    # Price features
    features["returns"] = df["close"].pct_change()
    features["log_returns"] = np.log1p(features["returns"])
    features["volatility"] = features["returns"].rolling(96).std()  # 24h
    
    # Volume features
    features["volume_ma"] = df["volume"].rolling(96).mean()
    features["volume_std"] = df["volume"].rolling(96).std()
    features["volume_ratio"] = df["volume"] / features["volume_ma"]
    
    # Technical indicators
    tech_features = calc_technical_features(df["close"])
    features = pd.concat([features, tech_features], axis=1)
    
    # Target variable (next period return)
    features["target"] = features["returns"].shift(-1) > 0
    
    # Drop NaN rows from lookback windows
    features = features.dropna()
    
    return features

def calc_technical_features(close: pd.Series) -> pd.DataFrame:
    """Calculate technical indicators"""
    features = pd.DataFrame(index=close.index)
    
    # Momentum
    features["rsi"] = talib.RSI(close)
    features["macd"], features["macd_signal"], _ = talib.MACD(close)
    
    # Trend
    features["ema_12"] = talib.EMA(close, timeperiod=12*4)  # 12h
    features["ema_24"] = talib.EMA(close, timeperiod=24*4)  # 24h
    
    # Volatility
    bb_upper, bb_middle, bb_lower = talib.BBANDS(close)
    features["bb_upper"] = bb_upper
    features["bb_middle"] = bb_middle
    features["bb_lower"] = bb_lower
    
    return features
