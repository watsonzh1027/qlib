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
        custom_keys = [
            'leverage', 'max_leverage', 'instrument_config', 
            'min_sigma_threshold', 'max_drawdown_limit',
            'target_symbols', 'max_hold_hours', 'stagnation_threshold',
            'trend_reversal_exit', 'trailing_sl'
        ]
        for key in custom_keys:
            if key in kwargs:
                self.custom_kwargs[key] = kwargs.pop(key)
        
        if signal is None:
            # Avoid create_signal_from(None) error in BaseSignalStrategy
            signal = pd.Series(dtype=float)
            
        super().__init__(signal=signal, risk_degree=risk_degree, **kwargs)
        
        self.leverage = self.custom_kwargs.get('leverage', 1.0)
        self.max_leverage = self.custom_kwargs.get('max_leverage', self.leverage)
        self.instrument_config = self.custom_kwargs.get('instrument_config', {})
        self.min_sigma_threshold = self.custom_kwargs.get('min_sigma_threshold', 0.0)
        self.max_drawdown_limit = self.custom_kwargs.get('max_drawdown_limit', 1.0)
        
        # New Parameters
        self.target_symbols = self.custom_kwargs.get('target_symbols', None)
        self.max_hold_hours = self.custom_kwargs.get('max_hold_hours', None) 
        self.stagnation_threshold = self.custom_kwargs.get('stagnation_threshold', 0.0)
        self.trend_reversal_exit = self.custom_kwargs.get('trend_reversal_exit', True)
        self.trailing_sl = self.custom_kwargs.get('trailing_sl', None) # e.g., -0.05
        
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
        
        # Entry tracking for SL/TP/Time
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
        # DEBUG LOGGING TO FILE
        debug_log_path = "logs/strategy_trace.log"
        with open(debug_log_path, "a") as f_dbg:
            f_dbg.write(f"\n--- STEP: {trade_start_time} ---\n")
            f_dbg.write(f"In Score Size: {len(score)}\n")
            if not score.empty:
                f_dbg.write(f"In Score Symbols: {score.index.tolist()}\n")
                f_dbg.write(f"Target Symbols: {self.target_symbols}\n")

            self._update_entry_info(current, trade_start_time)

            # 2. Update Prediction History & Calculate Sigma
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
                    sigmas[inst] = (val - mean) / std if std > 1e-6 else 0
                else:
                    sigmas[inst] = 0

            # 3. Process Exits (SL/TP, Trend Reversal, Stagnation, Time)
            active_exits = self._check_exit_conditions(current, score, sigmas, trade_start_time, trade_end_time)
            f_dbg.write(f"Active Exits: {active_exits}\n")
            
            # 4. Filter Potential Entries
            potential_entries = score.copy()
            
            if self.target_symbols is not None:
                potential_entries = potential_entries[potential_entries.index.isin(self.target_symbols)]
            f_dbg.write(f"Potential after Target Match: {len(potential_entries)}\n")
            
            # Exclude those already hitting exit this step
            potential_entries = potential_entries[~potential_entries.index.isin(active_exits)]
            
            # Signal Threshold Filtering (Magnitude)
            if self.signal_threshold > 0:
                potential_entries = potential_entries[potential_entries.abs() >= self.signal_threshold]
            f_dbg.write(f"Potential after Threshold ({self.signal_threshold}): {len(potential_entries)}\n")

            # Sigma Threshold Filtering (Relative Confidence)
            if self.min_sigma_threshold > 0:
                qualified = []
                for inst in potential_entries.index:
                    if abs(sigmas.get(inst, 0)) >= self.min_sigma_threshold:
                        qualified.append(inst)
                potential_entries = potential_entries[potential_entries.index.isin(qualified)]
            f_dbg.write(f"Potential after Sigma: {len(potential_entries)}\n")

            # 5. Determine Selection & Ranking
            ranking_score = potential_entries.abs().sort_values(ascending=False)
            target_weights = {}
            
            if self.direction == "long":
                eligible_idx = ranking_score[potential_entries[ranking_score.index] > 0].head(self.topk).index
            elif self.direction == "short":
                eligible_idx = ranking_score[potential_entries[ranking_score.index] < 0].head(self.topk).index
            else: # long-short
                eligible_idx = ranking_score.head(self.topk).index
            f_dbg.write(f"Eligible Index: {eligible_idx.tolist()}\n")

        # 6. Generate weights for Entries & Maintains
        # Current holdings not in active_exits should be maintained if they still meet basic criteria
        held_list = current.get_stock_list()
        final_list = list(set(list(eligible_idx) + [h for h in held_list if h not in active_exits]))
        
        # If we have a limit on topk and more candidates, we prioritize eligible_idx
        if len(final_list) > self.topk and self.target_symbols is None:
            # This is more for multi-symbol logic
            final_list = sorted(final_list, key=lambda x: potential_entries.get(x, 0), reverse=True)[:self.topk]

        for inst in final_list:
            if inst in active_exits:
                continue
                
            # Determine Side
            inst_score = score.get(inst, 0)
            if inst in held_list:
                side = self.entry_info[inst]["side"]
            else:
                if self.direction == "long-short":
                    side = 1 if inst_score >= 0 else -1
                elif self.direction == "short":
                    side = -1 
                else:
                    side = 1
            
            # Confidence-based Scaling: if sigma is high, use more leverage
            base_lev = self._get_param(inst, 'leverage', self.leverage)
            max_lev = self._get_param(inst, 'max_leverage', self.max_leverage)
            
            sigma_val = abs(sigmas.get(inst, 0))
            # Linear scaling between base_lev and max_lev based on sigma [min_sigma, 3.0]
            if sigma_val > self.min_sigma_threshold and max_lev > base_lev:
                scale = min(1.0, (sigma_val - self.min_sigma_threshold) / (3.0 - self.min_sigma_threshold))
                asset_lev = base_lev + (max_lev - base_lev) * scale
            else:
                asset_lev = base_lev
                
            target_weights[inst] = side * asset_lev
        
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

    def _update_entry_info(self, current: Position, trade_start_time: pd.Timestamp):
        """Update entry prices, peaks and times for currently held stocks"""
        held_list = current.get_stock_list()
        for inst in list(self.entry_info.keys()):
            if inst not in held_list:
                del self.entry_info[inst]
        
        for inst in held_list:
            curr_price = current.get_stock_price(inst)
            if inst not in self.entry_info:
                amount = current.get_stock_amount(inst)
                side = 1 if amount > 0 else -1
                self.entry_info[inst] = {
                    "price": curr_price, 
                    "side": side, 
                    "time": trade_start_time,
                    "peak_price": curr_price
                }
            else:
                # Update peak price for Trailing Stop
                side = self.entry_info[inst]["side"]
                if side == 1: # Long position, peak is max price
                    self.entry_info[inst]["peak_price"] = max(self.entry_info[inst]["peak_price"], curr_price)
                else: # Short position, peak is min price
                    self.entry_info[inst]["peak_price"] = min(self.entry_info[inst]["peak_price"], curr_price)

    def _check_exit_conditions(self, current: Position, score: pd.Series, sigmas: Dict[str, float], start_time: pd.Timestamp, end_time: pd.Timestamp) -> List[str]:
        """Comprehensive check for SL, Trailing SL, TP, Trend Reversal, and Stagnation."""
        exits = []
        held_list = current.get_stock_list()
        
        for inst in held_list:
            if inst not in self.entry_info:
                continue
                
            info = self.entry_info[inst]
            entry_price = info["price"]
            peak_price = info["peak_price"]
            side = info["side"]
            entry_time = info["time"]
            
            # Latest Close Price for SL/TP
            try:
                curr_price = self.trade_exchange.get_close(inst, start_time, end_time)
            except Exception:
                continue
            
            if curr_price is not None and not np.isnan(curr_price) and entry_price != 0:
                profit_pct = (curr_price / entry_price - 1.0) * side
                trailing_profit_pct = (curr_price / peak_price - 1.0) * side
                
                # 1. Fixed Stop Loss & Take Profit
                sl = self._get_param(inst, 'stop_loss', self.stop_loss)
                tp = self._get_param(inst, 'take_profit', self.take_profit)
                tsl = self._get_param(inst, 'trailing_sl', self.trailing_sl)
                
                if sl is not None and profit_pct <= sl:
                    logger.info(f"EXIT [SL] {inst} at {curr_price:.2f}: Entry={entry_price:.2f}, Profit={profit_pct:.2%}")
                    exits.append(inst)
                    continue
                if tsl is not None and trailing_profit_pct <= tsl:
                    logger.info(f"EXIT [TSL] {inst} at {curr_price:.2f}: Peak={peak_price:.2f}, Drop={trailing_profit_pct:.2%}")
                    exits.append(inst)
                    continue
                if tp is not None and profit_pct >= tp:
                    logger.info(f"EXIT [TP] {inst} at {curr_price:.2f}: Entry={entry_price:.2f}, Profit={profit_pct:.2%}")
                    exits.append(inst)
                    continue

            # 2. Trend Reversal
            inst_score = score.get(inst, 0)
            if self.trend_reversal_exit:
                # If Long and score is negative, or Short and score is positive
                if (side == 1 and inst_score < 0) or (side == -1 and inst_score > 0):
                    logger.info(f"EXIT [Reversal] {inst}: Side={side}, Score={inst_score:.4f}")
                    exits.append(inst)
                    continue
            
            # 3. Time-based Stagnation
            if self.max_hold_hours is not None:
                hold_duration = (start_time - entry_time).total_seconds() / 3600.0
                if hold_duration >= self.max_hold_hours:
                    # Check if stagnant (small predicted return)
                    if abs(inst_score) < self.stagnation_threshold:
                        logger.info(f"EXIT [Stag] {inst}: held {hold_duration:.1f}h, Score={inst_score:.4f}")
                        exits.append(inst)
                        continue

        return exits
