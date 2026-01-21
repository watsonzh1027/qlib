
import copy
import numpy as np
import pandas as pd
from typing import List, Tuple, Union, Dict

from qlib.strategy.base import BaseStrategy
from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.backtest.position import Position
from qlib.backtest.signal import Signal, create_signal_from
from qlib.log import get_module_logger

class RiskControlStrategy(BaseStrategy):
    """
    Simple Threshold Strategy with Risk Control.
    - Buy/Hold if signal > buy_threshold
    - Sell if signal < sell_threshold
    - Stop Loss / Take Profit overrides signal
    """
    def __init__(
        self,
        signal=None,
        buy_threshold=0.0, # Neutral 0
        sell_threshold=0.0,
        stop_loss: float = None,
        take_profit: float = None,
        risk_degree: float = 0.95,
        min_holding_days: int = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.signal = create_signal_from(signal)
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.risk_degree = risk_degree
        self.cost_basis: Dict[str, float] = {} 
        self.logger = get_module_logger("RiskControlStrategy")

    def _update_cost_basis(self, execute_result):
        if not execute_result:
            return

        current_pos = self.trade_position
        
        for record in execute_result:
            if len(record) == 4:
                order, val, cost, price = record
            else:
                continue 
            
            stock_id = order.stock_id
            
            if order.direction == Order.BUY:
                new_amt = order.deal_amount
                total_amt = current_pos.get_stock_amount(stock_id) # This is post-execution amount
                old_amt = total_amt - new_amt
                
                if old_amt < 1e-5:
                    self.cost_basis[stock_id] = price
                else:
                    prev_cost = self.cost_basis.get(stock_id, price)
                    # Weighted Avg
                    new_cost = ((old_amt * prev_cost) + (new_amt * price)) / total_amt
                    self.cost_basis[stock_id] = new_cost
                    
            elif order.direction == Order.SELL:
                remaining = current_pos.get_stock_amount(stock_id)
                if remaining < 1e-5 and stock_id in self.cost_basis:
                    del self.cost_basis[stock_id]

    def _sync_cost_basis_with_position(self):
        held_stocks = set(self.trade_position.get_stock_list())
        to_del = [s for s in self.cost_basis if s not in held_stocks]
        for s in to_del:
            del self.cost_basis[s]
        for s in held_stocks:
            if s not in self.cost_basis:
                self.cost_basis[s] = self.trade_position.get_stock_price(s)

    def generate_trade_decision(self, execute_result=None):
        # 1. Update Cost Basis
        if execute_result:
            self._update_cost_basis(execute_result)
        self._sync_cost_basis_with_position()
        
        # 2. Get Signal
        trade_step = self.trade_calendar.get_trade_step()
        trade_start_time, trade_end_time = self.trade_calendar.get_step_time(trade_step)
        pred_start_time, pred_end_time = self.trade_calendar.get_step_time(trade_step, shift=1)
        pred_score = self.signal.get_signal(start_time=pred_start_time, end_time=pred_end_time)
        
        if isinstance(pred_score, pd.DataFrame):
            pred_score = pred_score.iloc[:, 0] # Assume 1st col
            
        final_orders = []
        
        # 3. Iterate Instruments (Universe? Held + Signal)
        # Since we use pred_score as universe source
        if pred_score is None:
             candidates = []
        else:
             candidates = pred_score.index.tolist()
             
        held_stocks = self.trade_position.get_stock_list()
        all_stocks = set(candidates) | set(held_stocks)
        
        cash = self.trade_position.get_cash()
        # Roughly allocate cash to buy candidates?
        # Simple Logic: Only trade ETH_USDT (or whatever is in signal)
        
        for stock_id in all_stocks:
            score = pred_score.get(stock_id, -999) if pred_score is not None else -999
            current_amt = self.trade_position.get_stock_amount(stock_id)
            
            # Get price
            if self.trade_position.check_stock(stock_id):
                current_price = self.trade_position.get_stock_price(stock_id)
            else:
                 # Get from exchange
                 # trade_start_time is the time we are trading at. Last close is usually at 'pred_end_time' (which is trade_start_time?)
                 # Usually qlib exchange get_close uses lookup. 
                 # Let's use trade_start_time to trade_end_time
                 current_price = self.trade_exchange.get_close(stock_id, trade_start_time, trade_end_time)

            # Check validity
            if np.isnan(current_price) or current_price <= 0:
                continue
            
            # Risk Check
            force_sell = False
            if stock_id in self.cost_basis and current_amt > 0:
                cost = self.cost_basis[stock_id]
                if cost > 0:
                    pnl_pct = (current_price - cost) / cost
                    
                    if self.stop_loss and pnl_pct < -self.stop_loss:
                        force_sell = True
                        self.logger.info(f"SL Trigger: {stock_id} PnL {pnl_pct:.2%}")
                    elif self.take_profit and pnl_pct > self.take_profit:
                        force_sell = True
                        self.logger.info(f"TP Trigger: {stock_id} PnL {pnl_pct:.2%}")
            
            # Decision
            if force_sell:
                # Close position
                if current_amt > 0:
                    final_orders.append(Order(
                        stock_id=stock_id,
                        amount=current_amt,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=Order.SELL
                    ))
            else:
                # Normal Strategy
                if score > self.buy_threshold:
                    # Buy / Hold
                    if current_amt == 0:
                        # Buy
                        # How much? Full allocation implies 1 stock
                        # Use 95% of cash
                        invest_cash = cash * self.risk_degree
                        # Price? use last close as estimate
                        if not np.isnan(current_price) and current_price > 0:
                            buy_amt = invest_cash / current_price
                            # Rounding?
                            final_orders.append(Order(
                                stock_id=stock_id,
                                amount=buy_amt,
                                start_time=trade_start_time,
                                end_time=trade_end_time,
                                direction=Order.BUY
                            ))
                            cash -= invest_cash # Deduct virtual cash
                elif score < self.sell_threshold:
                    # Sell
                    if current_amt > 0:
                        final_orders.append(Order(
                            stock_id=stock_id,
                            amount=current_amt,
                            start_time=trade_start_time,
                            end_time=trade_end_time,
                            direction=Order.SELL
                        ))
        
        return TradeDecisionWO(final_orders, self)
