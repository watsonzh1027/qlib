import copy
import numpy as np
import pandas as pd
from typing import Dict, List, Union
from qlib.strategy.base import BaseStrategy
from qlib.backtest.position import Position
from qlib.backtest.exchange import Exchange
from qlib.utils import get_module_by_module_path

class MultiScaleEnsembleStrategy(BaseStrategy):
    """
    Multi-Scale Ensemble Strategy
    
    This strategy assumes that the predictions are passed in as a pre-calculated DataFrame 
    containing columns for each timeframe's prediction (e.g., 'score_240min', 'score_60min', 'score_15min').
    
    It applies dynamic weighting based on data availability (NaN checks).
    """
    def __init__(
        self, 
        signal: pd.Series, # Combined or Multi-col signal. Here we expect a DataFrame passed via some mechanism or we process it here.
                           # Actually Qlib BacktestExecutor passes the 'pred' result from model execution to the strategy's `generate_order_list`.
                           # But standard Qlib flow passes a single Series `pred_score`.
                           # For us, we will perform the pre-calculation and ensemble OUTSIDE, and pass the FINAL combined score to a simple TopK strategy.
                           # OR, we implement the logic inside `generate_trade_decision`.
                           
        # Let's support an "Online" mode where we might load models. 
        # But for efficiency, we assume 'signal' is ALREADY the combined signal or we pass a DataFrame index-aligned.
        
        # If we stick to the plan: "Pre-calculating the Combined Signal... is cleaner".
        # So this class might just be a standard TopK or Threshold strategy that consumes the 'combined_score'.
        
        # However, to support specific logic like Regime Filtering inside the strategy loop:
        threshold: float = 0.001,
        step: int = 1, # Rebalance freq
        risk_degree: float = 0.95,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.signal = signal
        self.threshold = threshold
        self.risk_degree = risk_degree
        self.step = step
        self.count = 0

    def generate_trade_decision(self, execute_result=None):
        # execute_result is not used here
        
        # Current trade step
        if self.count % self.step != 0:
            self.count += 1
            return []
        
        # Get current date
        # Strategy context/executor usually holds current time? 
        # BaseStrategy doesn't hold `current_time`. It depends on `common_infra`.
        # But `generate_trade_decision` is called by Executor which sets the context.
        # Actually Qlib strategy usually iterates dates in `run` if run manually.
        # But in `BacktestExecutor`, it calls `generate_trade_decision` at each step.
        
        # Wait, if we use `BacktestExecutor`, we don't have easy access to "current_time" unless we track it or use `trade_calendar`.
        # However, `self.signal` usually has MultiIndex (date, instrument).
        # We can implement a simple signal-based decision.
        
        # Let's assume `self.signal` IS the final combined alpha score.
        # So this strategy degenerates to a simple Threshold Strategy.
        pass

# Actually, to follow the plan "Scripts/run_multiscale_backtest.py... Pre-calculation... Combined Signal",
# We don't need a complex strategy class. A simple Rule-based strategy is enough.
# The "Smart" logic happens in the Pre-calculation step (merging 3 model preds).

# So I will implement the weighting logic in a utility function or script, 
# and here I define `weighted_ensemble` function that can be used by the script.

def dynamic_ensemble(df_preds: pd.DataFrame, weights: Dict[str, float] = None) -> pd.Series:
    """
    df_preds: DataFrame with columns ['240min', '60min', '15min'] (aligned index)
    weights: Base weights, e.g., {'240min': 0.5, '60min': 0.3, '15min': 0.2}
    """
    if weights is None:
        weights = {'240min': 0.5, '60min': 0.3, '15min': 0.2}
    
    # Check columns
    cols = ['240min', '60min', '15min']
    available_cols = [c for c in cols if c in df_preds.columns]
    
    # We process row by row or vectorized
    # Vectorized approach for "Dynamic Fallback":
    
    # 1. Mask of availability
    mask = df_preds[available_cols].notna()
    
    # 2. Base scores (fill NaN with 0 temporarily)
    scores = df_preds[available_cols].fillna(0)
    
    # 3. Dynamic Weights
    # If 15min is missing, drag its weight to 1h? Or re-normalize?
    # Logic:
    # Scheme A: Re-normalize available weights.
    
    # Create weight matrix with same shape
    w_matrix = pd.DataFrame(0.0, index=df_preds.index, columns=available_cols)
    for col in available_cols:
        w_matrix[col] = weights.get(col, 0.0)
    
    # Zero out weights where data is missing
    w_matrix = w_matrix * mask
    
    # Normalize rows to sum to 1.0
    w_sums = w_matrix.sum(axis=1)
    
    # Avoid division by zero (if all missing)
    w_sums = w_sums.replace(0, 1.0) # If all nan, sum is 0->1, result is 0
    
    w_norm = w_matrix.div(w_sums, axis=0)
    
    # 4. Final Score
    final_score = (scores * w_norm).sum(axis=1)
    
    # If all missing, result is 0 (from fillna(0) * 0)
    # Set back to NaN where all inputs were NaN
    all_nan = (~mask).all(axis=1)
    final_score[all_nan] = np.nan
    
    return final_score

