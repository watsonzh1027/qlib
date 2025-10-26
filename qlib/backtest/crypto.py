import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path
import yaml
import json

class BacktestEngine:
    """Cryptocurrency trading strategy backtester"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.fee_rate = self.config["trading"]["costs"]["fee"]
        self.slippage = self.config["trading"]["costs"]["slippage"]
        self.max_position = self.config["trading"]["position"]["max_size"]
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        if config_path is None:
            config_path = Path(__file__).parent.parent / "features/crypto-workflow/config_defaults.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def run(self, prices: pd.DataFrame, signals: pd.DataFrame) -> Dict:
        """Execute backtest and return results"""
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
                position = target_position
            
            # Update equity curve
            equity_curve.loc[timestamp, "position"] = position
            equity_curve.loc[timestamp, "equity"] = self._calculate_equity(
                position=position,
                price=current_price["close"],
                prev_equity=equity_curve["equity"].iloc[-2] if len(equity_curve) > 1 else 1.0
            )
        
        # Calculate performance metrics
        metrics = self._calculate_metrics(equity_curve, trades)
        
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
        cost = abs(size) * executed_price * self.fee_rate
        
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
        return float(drawdown.min())
    
    def _calculate_win_rate(self, trades: list) -> float:
        """Calculate percentage of profitable trades"""
        if not trades:
            return 0
        profits = [t["size"] * (t["price"] - t["cost"]) for t in trades]
        return sum(p > 0 for p in profits) / len(profits)
