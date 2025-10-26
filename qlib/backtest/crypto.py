import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path
import yaml
import json
from qlib.utils.logging import setup_logger

class BacktestEngine:
    """Cryptocurrency trading strategy backtester"""
    
    def __init__(self, config_path: Optional[str] = None, fee_rate: Optional[float] = None,
                 slippage: Optional[float] = None, max_position: Optional[float] = None):
        self.logger = setup_logger("backtest.crypto")
        self.config = self._load_config(config_path)
        self.fee_rate = fee_rate if fee_rate is not None else self.config["trading"]["costs"]["fee"]
        self.slippage = slippage if slippage is not None else self.config["trading"]["costs"]["slippage"]
        self.max_position = max_position if max_position is not None else self.config["trading"]["position"]["max_size"]
        self.cash = 1.0  # Initialize cash for tracking
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        if config_path is None:
            config_path = Path(__file__).parent.parent / "features/crypto-workflow/config_defaults.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def run(self, prices: pd.DataFrame, signals: pd.DataFrame) -> Dict:
        self.logger.info("Starting backtest simulation", extra={
            "start_date": prices.index[0].isoformat(),
            "end_date": prices.index[-1].isoformat(),
            "n_signals": len(signals)
        })
        
        # Initialize portfolio tracking
        equity_curve = self._initialize_equity_curve(prices.index)
        trades = []
        position = 0

        # Simulate trading
        for timestamp in prices.index:
            signal = signals.loc[timestamp]
            current_price = prices.loc[timestamp]

            # Calculate target position
            target_position = self._calculate_target_position(signal)

            # Execute trade if needed
            if target_position != position:
                trade = self._execute_trade(
                    timestamp=timestamp,
                    current_position=position,
                    target_position=target_position,
                    price=current_price,
                    signal_score=signal["score"]
                )
                trades.append(trade)
                # Deduct cost from cash
                self.cash -= trade["cost"]
                position = target_position

            # Update equity curve
            equity_curve.loc[timestamp, "position"] = position
            equity_curve.loc[timestamp, "cash"] = self.cash
            equity_curve.loc[timestamp, "equity"] = self._calculate_equity(
                position=position,
                price=current_price["close"]
            )
        
        # Calculate performance metrics
        metrics = self._calculate_metrics(equity_curve, trades)
        
        self.logger.info("Backtest completed", extra={
            "metrics": metrics,
            "trade_count": len(trades)
        })
        return {
            "equity_curve": equity_curve,
            "trades": pd.DataFrame(trades),
            "metrics": metrics
        }
    
    def _calculate_target_position(self, signal) -> float:
        """Calculate target position size with limits"""
        position = float(signal["position_size"])
        return np.clip(position, -self.max_position, self.max_position)
    
    def _execute_trade(self, timestamp, current_position, target_position, 
                      price, signal_score) -> Dict:
        """Execute trade with transaction costs"""
        size = target_position - current_position
        executed_price = price["open"] * (1 + np.sign(size) * self.slippage)
        cost = abs(size) * executed_price * (self.fee_rate + self.slippage)

        self.logger.debug("Trade executed", extra={
            "timestamp": timestamp.isoformat(),
            "size": size,
            "price": executed_price,
            "cost": cost
        })

        return {
            "timestamp": timestamp,
            "size": size,
            "price": executed_price,
            "cost": cost,
            "score": signal_score
        }
    
    def _calculate_metrics(self, equity_curve: pd.DataFrame, trades: list) -> Dict:
        """Calculate performance metrics"""
        returns = equity_curve["equity"].pct_change().dropna()
        
        metrics = {
            "total_return": float(equity_curve["equity"].iloc[-1] / equity_curve["equity"].iloc[0] - 1),
            "sharpe_ratio": self._calculate_sharpe_ratio(returns),
            "max_drawdown": self._calculate_max_drawdown(equity_curve["equity"]),
            "win_rate": self._calculate_win_rate(trades),
            "trade_count": len(trades)
        }
        return metrics
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate annualized Sharpe ratio"""
        annual_factor = np.sqrt(365 * 24 * 4)  # 15-min bars
        return returns.mean() / returns.std() * annual_factor if len(returns) > 0 else 0
    
    def _calculate_max_drawdown(self, equity: pd.Series) -> float:
        """Calculate maximum drawdown percentage"""
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak
        drawdown_clean = drawdown.dropna()
        if drawdown_clean.empty:
            return 0.0
        min_drawdown = np.nanmin(drawdown_clean.values)
        if not np.isfinite(min_drawdown):
            return 0.0
        return float(min_drawdown)
    
    def _calculate_win_rate(self, trades: list) -> float:
        """Calculate percentage of profitable trades"""
        if not trades:
            return 0
        profits = [t["size"] * (t["price"] - t["cost"]) for t in trades]
        return sum(p > 0 for p in profits) / len(profits)

    def _initialize_equity_curve(self, index: pd.DatetimeIndex) -> pd.DataFrame:
        """Initialize equity curve DataFrame"""
        return pd.DataFrame({
            "position": 0.0,
            "equity": 1.0,
            "cash": 1.0
        }, index=index)

    def _calculate_equity(self, position: float, price: float) -> float:
        """Calculate current equity as cash + position value"""
        return self.cash + position * price
