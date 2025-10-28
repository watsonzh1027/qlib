import numpy as np
import pandas as pd
from typing import Dict, Union, List
from enum import Enum

class FeatureGroup(Enum):
    """Groups of alpha features by type."""
    PRICE = "price"
    VOLUME = "volume"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"

class Alpha360Calculator:
    """Calculates Alpha360 features grouped by type."""
    
    def __init__(self, selected_groups: List[FeatureGroup] = None, max_features_per_group: int = 10):
        self.selected_groups = selected_groups or list(FeatureGroup)
        self.max_features = max_features_per_group
        self._feature_functions = self._init_feature_functions()
    
    def _init_feature_functions(self) -> Dict:
        """Initialize feature functions by group."""
        return {
            FeatureGroup.PRICE: {
                # Price action features (most effective first based on research)
                'alpha001': lambda x: self._price_alpha001(x),  # Close price momentum
                'alpha002': lambda x: self._price_alpha002(x),  # Price range breakout
                'alpha003': lambda x: self._price_alpha003(x),  # Moving average crossover
                'alpha004': lambda x: self._price_alpha004(x),  # Price acceleration
                'alpha005': lambda x: self._price_alpha005(x),  # Price reversal
            },
            FeatureGroup.VOLUME: {
                'alpha101': lambda x: self._volume_alpha001(x),  # Volume price correlation
                'alpha102': lambda x: self._volume_alpha002(x),  # Volume surge
                'alpha103': lambda x: self._volume_alpha003(x),  # Volume trend
                'alpha104': lambda x: self._volume_alpha004(x),  # Volume price divergence
                'alpha105': lambda x: self._volume_alpha005(x),  # Volume weighted price
            },
            FeatureGroup.MOMENTUM: {
                'alpha201': lambda x: self._momentum_alpha001(x),  # RSI variation
                'alpha202': lambda x: self._momentum_alpha002(x),  # MACD signal
                'alpha203': lambda x: self._momentum_alpha003(x),  # Triple momentum
                'alpha204': lambda x: self._momentum_alpha004(x),  # Momentum breakout
                'alpha205': lambda x: self._momentum_alpha005(x),  # Momentum reversal
            },
            FeatureGroup.VOLATILITY: {
                'alpha301': lambda x: self._volatility_alpha001(x),  # ATR based
                'alpha302': lambda x: self._volatility_alpha002(x),  # Bollinger squeeze
                'alpha303': lambda x: self._volatility_alpha003(x),  # Volatility breakout
                'alpha304': lambda x: self._volatility_alpha004(x),  # Volatility trend
                'alpha305': lambda x: self._volatility_alpha005(x),  # Volatility mean reversion
            }
        }

    # Price action features
    def _price_alpha001(self, ohlcv: pd.DataFrame) -> pd.Series:
        """(rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)"""
        returns = ohlcv['close'].pct_change()
        inner = np.where(returns < 0, returns.rolling(20).std(), ohlcv['close'])
        return rank(ts_argmax(pd.Series(inner, index=ohlcv.index) ** 2, 5)) - 0.5

    def _price_alpha002(self, ohlcv: pd.DataFrame) -> pd.Series:
        """(-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))"""
        volume_factor = rank(delta(np.log(ohlcv['volume']), 2))
        price_factor = rank((ohlcv['close'] - ohlcv['open']) / ohlcv['open'])
        return -1 * correlation(volume_factor, price_factor, 6)

    def _price_alpha003(self, ohlcv: pd.DataFrame) -> pd.Series:
        """(-1 * correlation(rank(high), rank(volume), 5))"""
        return -1 * correlation(rank(ohlcv['high']), rank(ohlcv['volume']), 5)

    def _price_alpha004(self, ohlcv: pd.DataFrame) -> pd.Series:
        """(-1 * Ts_Rank(rank(low), 9))"""
        return -1 * ts_rank(rank(ohlcv['low']), 9)

    def _price_alpha005(self, ohlcv: pd.DataFrame) -> pd.Series:
        """(rank((open - (sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap)))))"""
        vwap = (ohlcv['high'] + ohlcv['low'] + ohlcv['close']) / 3  # Simplified VWAP
        return rank(ohlcv['open'] - (vwap.rolling(10).sum() / 10)) * (-1 * abs(rank(ohlcv['close'] - vwap)))

    # Volume features
    def _volume_alpha001(self, ohlcv: pd.DataFrame) -> pd.Series:
        """(-1 * correlation(open, volume, 10))"""
        return -1 * correlation(ohlcv['open'], ohlcv['volume'], 10)

    def _volume_alpha002(self, ohlcv: pd.DataFrame) -> pd.Series:
        """((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 10)) * sign(delta(close, 7))) : (-1 * 1))"""
        adv20 = ohlcv['volume'].rolling(20).mean()
        delta_close = delta(ohlcv['close'], 7)
        ts_rank_result = ts_rank(abs(delta_close), 10)
        return np.where(adv20 < ohlcv['volume'],
                       (-1 * ts_rank_result) * np.sign(delta_close),
                       -1)

    def _volume_alpha003(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Volume trend"""
        return rank(ohlcv['volume'].pct_change(5))

    def _volume_alpha004(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Volume price divergence"""
        volume_change = ohlcv['volume'].pct_change(5)
        price_change = ohlcv['close'].pct_change(5)
        return correlation(volume_change, price_change, 10)

    def _volume_alpha005(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Volume weighted price"""
        vwap = (ohlcv['close'] * ohlcv['volume']).rolling(10).sum() / ohlcv['volume'].rolling(10).sum()
        return rank(vwap)

    # Momentum features
    def _momentum_alpha001(self, ohlcv: pd.DataFrame) -> pd.Series:
        """RSI variation"""
        delta_close = delta(ohlcv['close'], 1)
        gain = np.where(delta_close > 0, delta_close, 0)
        loss = np.where(delta_close < 0, -delta_close, 0)
        avg_gain = pd.Series(gain, index=ohlcv.index).rolling(14).mean()
        avg_loss = pd.Series(loss, index=ohlcv.index).rolling(14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rank(rsi)

    def _momentum_alpha002(self, ohlcv: pd.DataFrame) -> pd.Series:
        """MACD signal"""
        ema12 = ohlcv['close'].ewm(span=12, adjust=False).mean()
        ema26 = ohlcv['close'].ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        return rank(macd)

    def _momentum_alpha003(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Triple momentum"""
        mom1 = delta(ohlcv['close'], 1)
        mom2 = delta(ohlcv['close'], 2)
        mom3 = delta(ohlcv['close'], 3)
        return rank(mom1 + mom2 + mom3)

    def _momentum_alpha004(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Momentum breakout"""
        return np.where(ohlcv['close'] > ohlcv['close'].rolling(20).mean(), 1, -1)

    def _momentum_alpha005(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Momentum reversal"""
        return -1 * rank(delta(ohlcv['close'], 5))

    # Volatility features
    def _volatility_alpha001(self, ohlcv: pd.DataFrame) -> pd.Series:
        """ATR based"""
        tr = np.maximum(ohlcv['high'] - ohlcv['low'], 
                        np.maximum(abs(ohlcv['high'] - ohlcv['close'].shift()), 
                                   abs(ohlcv['low'] - ohlcv['close'].shift())))
        atr = tr.rolling(window=14).mean()
        return rank(atr)

    def _volatility_alpha002(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Bollinger squeeze"""
        sma20 = ohlcv['close'].rolling(window=20).mean()
        std20 = ohlcv['close'].rolling(window=20).std()
        return (ohlcv['close'] - sma20) / (2 * std20)

    def _volatility_alpha003(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Volatility breakout"""
        return np.where(ohlcv['close'] > ohlcv['close'].rolling(20).mean() + 2 * ohlcv['close'].rolling(20).std(), 1, 0)

    def _volatility_alpha004(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Volatility trend"""
        return ts_rank(ohlcv['close'].rolling(20).std(), 10)

    def _volatility_alpha005(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Volatility mean reversion"""
        return -1 * rank(ohlcv['close'].rolling(20).std())

    def calculate_features(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Calculate features for selected groups."""
        features = {}
        
        for group in self.selected_groups:
            group_funcs = self._feature_functions[group]
            for name, func in group_funcs.items():
                features[name] = func(ohlcv)
        
        return pd.DataFrame(features)

# Helper functions
def rank(series: pd.Series) -> pd.Series:
    """Cross-sectional rank."""
    return series.rank(pct=True)

def ts_argmax(series: pd.Series, window: int) -> pd.Series:
    """Rolling argmax."""
    return series.rolling(window).apply(lambda x: np.argmax(x.values))

def delta(series: pd.Series, periods: int = 1) -> pd.Series:
    """Calculate the difference of a Series element compared with another element in the Series and used for calculating returns."""
    return series.diff(periods)

def correlation(series1: pd.Series, series2: pd.Series, window: int) -> pd.Series:
    """Calculate the rolling correlation between two series."""
    return series1.rolling(window).corr(series2)

def ts_rank(series: pd.Series, window: int) -> pd.Series:
    """Calculate the rolling rank of a series."""
    return series.rolling(window).rank(pct=True)
