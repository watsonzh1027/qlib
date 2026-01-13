from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from qlib.backtest.position import Position
from qlib.backtest.decision import TradeDecisionWO
from qlib.log import get_module_logger
from qlib.contrib.strategy.signal_strategy import WeightStrategyBase

logger = get_module_logger("CryptoLongShortStrategy")

class CryptoLongShortStrategy(WeightStrategyBase):
    """
    Enhanced Weight-based Strategy for Crypto (e.g. single-symbol or few-symbol).
    Condition: trade only if predicted return magnitude exceeds a threshold.
    """

    def __init__(
        self,
        signal: Any = None,
        topk: int = 1,
        direction: str = "long-short",
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        signal_threshold: float = 0.0,
        risk_degree: float = 1.0,
        **kwargs
    ):
        # We should pop custom keys that BaseStrategy doesn't expect
        self.custom_kwargs = {}
        for key in ['leverage', 'instrument_config', 'min_sigma_threshold', 'max_drawdown_limit']:
            if key in kwargs:
                self.custom_kwargs[key] = kwargs.pop(key)
        
        if signal is None:
            # Avoid create_signal_from(None) error in BaseSignalStrategy
            signal = pd.Series(dtype=float)
            
        super().__init__(signal=signal, risk_degree=risk_degree, **kwargs)
        
        self.leverage = self.custom_kwargs.get('leverage', 1.0)
        self.instrument_config = self.custom_kwargs.get('instrument_config', {})
        self.min_sigma_threshold = self.custom_kwargs.get('min_sigma_threshold', 0.0)
        self.max_drawdown_limit = self.custom_kwargs.get('max_drawdown_limit', 0.25)
        
        self.topk = topk
        self.direction = direction.lower()
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.signal_threshold = signal_threshold
        
        # Portfolio State for Circuit Breaker
        self.peak_value = 0.0
        self.last_risk_scale = 1.0
        
        # Prediction History for Sigma calculation (Confidence)
        self.prediction_history: Dict[str, List[float]] = {}
        self.max_history = 100 
        
        # Entry tracking for SL/TP
        self.entry_info = {} 

    def _get_param(self, instrument: str, param: str, default: Any) -> Any:
        """Get parameter for a specific instrument, falling back to default/global."""
        if instrument in self.instrument_config:
            return self.instrument_config[instrument].get(param, default)
        
        # Try simplified name (e.g. BTC for BTC/USDT)
        base_symbol = instrument.split("/")[0] if "/" in instrument else instrument
        if base_symbol in self.instrument_config:
            return self.instrument_config[base_symbol].get(param, default)
            
        return default 

    def generate_target_weight_position(self, score: pd.Series, current: Position, trade_start_time: pd.Timestamp, trade_end_time: pd.Timestamp) -> Dict[str, float]:
        """
        Generate target weights based on predictions.
        """
        if isinstance(score, pd.DataFrame):
            score = score.iloc[:, 0]
        
        if score is None or score.empty:
            return {}

        # 1. Update Entry Prices for new/existing positions
        self._update_entry_info(current)

        # 2. Check for SL/TP hits (Risk Management)
        excl_instruments = self._check_risk_hits(current, trade_start_time, trade_end_time)

        # 3. Filter Excluded Instruments
        if excl_instruments:
            score = score[~score.index.isin(excl_instruments)]
        
        if score.empty:
            return {}

        # 4. Update Prediction History & Calculate Sigma (Confidence)
        sigmas = {}
        for inst, val in score.items():
            if inst not in self.prediction_history:
                self.prediction_history[inst] = []
            
            self.prediction_history[inst].append(val)
            if len(self.prediction_history[inst]) > self.max_history:
                self.prediction_history[inst].pop(0)
            
            if len(self.prediction_history[inst]) > 5:
                series = pd.Series(self.prediction_history[inst])
                std = series.std()
                mean = series.mean()
                if std > 1e-6:
                    sigmas[inst] = (val - mean) / std
                else:
                    sigmas[inst] = 0
            else:
                sigmas[inst] = 0

        # 5. Filter by Threshold (Absolute Magnitude)
        if self.signal_threshold > 0:
            score = score[score.abs() >= self.signal_threshold]
            
        if score.empty:
            return {}

        # 6. Sigma Threshold Filtering (Relative Magnitude)
        if self.min_sigma_threshold > 0:
            qualified_signals = {}
            for inst in score.index:
                sigma_val = abs(sigmas.get(inst, 0))
                if sigma_val >= self.min_sigma_threshold:
                    qualified_signals[inst] = score[inst]
            
            if not qualified_signals:
                return {}
            score = pd.Series(qualified_signals)

        # 7. Selection & Ranking
        ranking_score = score.abs().sort_values(ascending=False)
        target_weights = {}
        
        if self.direction == "long":
            eligible_idx = ranking_score[score[ranking_score.index] > 0].head(self.topk).index
        elif self.direction == "short":
            eligible_idx = ranking_score[score[ranking_score.index] < 0].head(self.topk).index
        else: # long-short
            eligible_idx = ranking_score.head(self.topk).index

        # Generate weights with leverage
        if len(eligible_idx) > 0:
            for inst in eligible_idx:
                asset_lev = self._get_param(inst, 'leverage', self.leverage)
                
                # Determine Side
                if self.direction == "long-short":
                    side = 1 if score[inst] >= 0 else -1
                elif self.direction == "short":
                    side = -1 
                else: # long
                    side = 1
                
                # Weight = (1 / K) * Leverage * Side
                target_weights[inst] = (1.0 / self.topk) * asset_lev * side
        
        # 8. Portfolio Circuit Breaker
        try:
            total_value = current.calculate_value()
            if self.peak_value == 0 or total_value > self.peak_value:
                self.peak_value = total_value
            
            drawdown = 1.0 - (total_value / self.peak_value) if self.peak_value > 0 else 0
            risk_scale = 1.0
            if drawdown > self.max_drawdown_limit + 0.10:
                risk_scale = 0.0
            elif drawdown > self.max_drawdown_limit:
                risk_scale = 0.5
            
            # Only log when state changes
            if risk_scale != self.last_risk_scale:
                if risk_scale == 0.0:
                    logger.warning(f"CIRCUIT BREAKER ACTIVATED: Drawdown {drawdown:.2%} hard stop (Scale: 0.0).")
                elif risk_scale == 0.5:
                    logger.warning(f"CIRCUIT BREAKER ACTIVATED: Drawdown {drawdown:.2%} soft scaling (Scale: 0.5).")
                else:
                    logger.info(f"CIRCUIT BREAKER RECOVERED: Drawdown {drawdown:.2%} back to normal (Scale: 1.0).")
                self.last_risk_scale = risk_scale

            if risk_scale != 1.0:
                for inst in target_weights:
                    target_weights[inst] *= risk_scale
                    
        except Exception as e:
            logger.error(f"Error in Circuit Breaker: {e}")

        return target_weights

    def _update_entry_info(self, current: Position):
        """Update entry prices for currently held stocks"""
        held_list = current.get_stock_list()
        for inst in list(self.entry_info.keys()):
            if inst not in held_list:
                del self.entry_info[inst]
        
        for inst in held_list:
            if inst not in self.entry_info:
                price = current.get_stock_price(inst)
                amount = current.get_stock_amount(inst)
                side = 1 if amount > 0 else -1
                self.entry_info[inst] = {"price": price, "side": side}

    def _check_risk_hits(self, current: Position, start_time: pd.Timestamp, end_time: pd.Timestamp) -> List[str]:
        """Check if any held stock hits Stop Loss or Take Profit"""
        excl = []
        if self.take_profit is None and self.stop_loss is None:
            return excl

        held_list = current.get_stock_list()
        for inst in held_list:
            if inst not in self.entry_info:
                continue
                
            entry_price = self.entry_info[inst]["price"]
            side = self.entry_info[inst]["side"]
            
            try:
                # Use trade_exchange to get the latest close price
                curr_price = self.trade_exchange.get_close(inst, start_time, end_time)
            except Exception:
                continue

            if curr_price is None or np.isnan(curr_price) or entry_price == 0:
                continue

            profit_pct = (curr_price / entry_price - 1.0) * side
            sl_threshold = self._get_param(inst, 'stop_loss', self.stop_loss)
            tp_threshold = self._get_param(inst, 'take_profit', self.take_profit)

            if sl_threshold is not None and profit_pct <= sl_threshold:
                logger.info(f"STOP LOSS hit for {inst}: profit={profit_pct:.2%}")
                excl.append(inst)
            elif tp_threshold is not None and profit_pct >= tp_threshold:
                logger.info(f"TAKE PROFIT hit for {inst}: profit={profit_pct:.2%}")
                excl.append(inst)
                
        return excl
