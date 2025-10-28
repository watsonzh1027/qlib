import pandas as pd
import numpy as np

DEFAULT_THRESHOLDS = {
    'buy': 0.7,
    'sell': 0.3,
    'max_position': 1.0
}

def score_to_signal(
    scores_df: pd.DataFrame,
    config: dict = None
) -> pd.DataFrame:
    """Convert prediction scores to trading signals and position sizes."""
    thresholds = DEFAULT_THRESHOLDS.copy()
    if config:
        thresholds.update(config)
    
    def _get_signal(score):
        if score >= thresholds['buy']:
            return 'BUY'
        elif score <= thresholds['sell']:
            return 'SELL'
        return 'HOLD'
    
    def _get_position_size(score):
        # Normalize score to [0,1] and scale by max position
        norm_score = (score - thresholds['sell']) / (thresholds['buy'] - thresholds['sell'])
        norm_score = np.clip(norm_score, 0, 1)
        return norm_score * thresholds['max_position']
    
    signals_df = scores_df.copy()
    signals_df['signal'] = signals_df['score'].apply(_get_signal)
    signals_df['position_size'] = signals_df['score'].apply(_get_position_size)
    
    return signals_df
