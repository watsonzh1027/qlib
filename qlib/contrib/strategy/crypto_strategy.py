# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
A lightweight crypto-oriented strategy for qlib:

CryptoTopNStrategy
 - choose top-N symbols by predicted absolute movement (long & short)
 - support intraday, shorting and leverage cap
 - simple equal-risk or equal-dollar sizing

This implementation is intentionally small and relies on qlib's Backtest Exchange/Position
interfaces for execution, fees and tradability checks.
"""
from typing import List, Tuple, Optional
import copy
import numpy as np
import pandas as pd

from qlib.contrib.strategy.signal_strategy import BaseSignalStrategy
from qlib.backtest.decision import Order
from qlib.backtest.decision import TradeDecisionWO
from qlib.backtest.position import Position
from qlib.log import get_module_logger

logger = get_module_logger("CryptoTopNStrategy")


class CryptoTopNStrategy(BaseSignalStrategy):
    """
    Crypto-oriented top-N strategy.

    Behavior:
      - for given universe (<=100), compute predicted change magnitude (abs(signal))
      - sort by magnitude and pick top_n (N<5 recommended)
      - place long orders for positive signals, short orders for negative signals
      - support leverage cap (sum(abs(weights)) <= max_leverage)
      - two sizing modes: 'equal_dollar' or 'equal_risk' (by volatility)

    Parameters
    ----------
    universe: Optional[List[str]]
        list of symbols to restrict to (if None, use signal index)
    top_n: int
        number of symbols to trade each decision (recommended <5)
    max_leverage: float
        maximum gross leverage (sum absolute weights), e.g. 5 for up to 5x
    sizing: str
        'equal_dollar' or 'equal_risk'
    vol_lookback: int
        lookback bars to estimate volatility (for equal_risk)
    only_tradable: bool
        whether to filter by tradability before placing orders
    """

    def __init__(
        self,
        *,
        universe: Optional[List[str]] = None,
        top_n: int = 3,
        max_leverage: float = 3.0,
        sizing: str = "equal_dollar",
        vol_lookback: int = 20,
        only_tradable: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.universe = universe
        self.top_n = top_n
        self.max_leverage = float(max_leverage)
        self.sizing = sizing
        self.vol_lookback = vol_lookback
        self.only_tradable = only_tradable

    def _get_signal_series(self, pred_score: pd.Series) -> pd.Series:
        # If pred_score is DataFrame, take first column
        if isinstance(pred_score, pd.DataFrame):
            pred_score = pred_score.iloc[:, 0]
        return pred_score

    def _estimate_vol(self, symbols: List[str], end_time, freq: str) -> pd.Series:
        # simple historical vol estimator using close returns
        try:
            df = self.dataset.prepare("trade") if hasattr(self, "dataset") else None
        except Exception:
            df = None
        # fallback: use D.features to pull recent close returns
        from qlib.data import D

        start = None
        if end_time is not None:
            # get vol_lookback bars before end_time
            start = pd.Timestamp(end_time) - pd.Timedelta(minutes=self.vol_lookback * 60)
        try:
            price_df = D.features(symbols, ["$close"], start, end_time, freq=freq, disk_cache=1)
            # compute std of returns grouped by instrument
            vol = (
                price_df.groupby(level=0)["$close"].apply(lambda s: s.pct_change().tail(self.vol_lookback).std())
            )
            vol = vol.fillna(method="ffill").fillna(1e-6)
            return vol
        except Exception:
            # best-effort fallback: equal volatility
            return pd.Series(1.0, index=symbols)

    def generate_trade_decision(self, execute_result=None):
        trade_step = self.trade_calendar.get_trade_step()
        trade_start_time, trade_end_time = self.trade_calendar.get_step_time(trade_step)
        pred_start_time, pred_end_time = self.trade_calendar.get_step_time(trade_step, shift=1)

        pred_score = self.signal.get_signal(start_time=pred_start_time, end_time=pred_end_time)
        if pred_score is None:
            return TradeDecisionWO([], self)

        pred_score = self._get_signal_series(pred_score)

        # restrict universe
        if self.universe is not None:
            pred_score = pred_score.reindex(self.universe).dropna()

        # compute absolute magnitude and pick top_n
        # prefer larger predicted move (abs value)
        ranked = pred_score.abs().sort_values(ascending=False)
        top_candidates = list(ranked.index[: self.top_n])
        if len(top_candidates) == 0:
            return TradeDecisionWO([], self)

        # optionally filter tradable
        if self.only_tradable:
            top_candidates = [s for s in top_candidates if self.trade_exchange.is_stock_tradable(s, trade_start_time, trade_end_time)]
            if len(top_candidates) == 0:
                return TradeDecisionWO([], self)

        # get direction signs (+1 for long, -1 for short)
        signs = {s: int(np.sign(pred_score.loc[s])) if pred_score.loc[s] != 0 else 1 for s in top_candidates}

        # sizing
        # get vol estimates for equal_risk
        weights = {}
        if self.sizing == "equal_risk":
            vol = self._estimate_vol(top_candidates, pred_end_time, freq=self.trade_calendar.get_freq())
            # risk budgets equal across legs
            inv_vol = 1.0 / vol.reindex(top_candidates).values
            raw = inv_vol / np.nansum(inv_vol)
            for s, r in zip(top_candidates, raw):
                weights[s] = r * signs[s]
        else:  # equal_dollar
            raw = np.ones(len(top_candidates)) / len(top_candidates)
            for s, r in zip(top_candidates, raw):
                weights[s] = r * signs[s]

        # apply leverage cap: scale weights so sum(abs) <= max_leverage
        gross = sum(abs(w) for w in weights.values())
        if gross > self.max_leverage:
            scale = self.max_leverage / gross
            for s in weights:
                weights[s] *= scale

        # convert weights to order amounts using current portfolio value
        current_temp: Position = copy.deepcopy(self.trade_position)
        portfolio_value = current_temp.calculate_value() if hasattr(current_temp, "calculate_value") else current_temp.get_cash()
        if portfolio_value == 0:
            portfolio_value = current_temp.get_cash()

        buy_orders = []
        sell_orders = []

        for s, w in weights.items():
            target_value = w * portfolio_value * self.get_risk_degree()
            # convert negative target_value -> short (sell) order, positive -> buy
            if target_value > 0:
                # place buy order for target_value
                price = self.trade_exchange.get_deal_price(s, trade_start_time, trade_end_time, direction=Order.BUY)
                amount = target_value / price if price and price > 0 else 0
                amount = self.trade_exchange.round_amount_by_trade_unit(amount, self.trade_calendar.get_freq())
                if amount > 0:
                    o = Order(stock_id=s, amount=amount, start_time=trade_start_time, end_time=trade_end_time, direction=Order.BUY)
                    if self.trade_exchange.check_order(o):
                        buy_orders.append(o)
            elif target_value < 0:
                # short: implement as sell order; exchange must support shorting semantics
                price = self.trade_exchange.get_deal_price(s, trade_start_time, trade_end_time, direction=Order.SELL)
                amount = abs(target_value) / price if price and price > 0 else 0
                amount = self.trade_exchange.round_amount_by_trade_unit(amount, self.trade_calendar.get_freq())
                if amount > 0:
                    o = Order(stock_id=s, amount=amount, start_time=trade_start_time, end_time=trade_end_time, direction=Order.SELL)
                    if self.trade_exchange.check_order(o):
                        sell_orders.append(o)

        return TradeDecisionWO(sell_orders + buy_orders, self)
