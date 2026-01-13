# Issue: Enhance Model Quality and Feature Engineering for ETH Trading

## Status: OPEN

## Problem Description
The initial backtest results for ETH 4H trading showed poor annualized returns and high drawdowns. The objective is to systematically improve the predictive quality of the models (LightGBM and ALSTM) and optimize the trading strategy.

## Progress Summary
1.  **Feature Enhancement**:
    *   Integrated `Alpha158` and `Alpha360` feature sets.
    *   Added custom features: `range` (volatility), `vwap_dev` (price deviation), and `rsv10`.
    *   Implemented **Cyclical Encoding** for time features (`weekday`, `hour`) using `Sin/Cos` transformations.
    *   Registered `Sin` and `Cos` operators in Qlib's expression engine (`qlib/data/ops.py`).
2.  **Label Optimization**:
    *   Changed target label to 3-period forward return (`Ref($close, -3)/$close - 1`).
    *   Switched to `RobustZScoreNorm` for features and ensured stable label distribution.
3.  **Model Robustness**:
    *   Implemented `Huber Loss` for both LightGBM and ALSTM to handle crypto market outliers.
    *   Increased ALSTM sequence length to 60 and dropout to 0.5.
4.  **Foundational Showdown**:
    *   Conducted a showdown between LightGBM and ALSTM on strictly ETH data.
    *   **LightGBM showed promising results with IC = 0.0625 and Sharpe = 0.40.**
    *   ALSTM showed higher instability and lower IC on the current single-symbol setup.

## Current Results (ETH 4H)
| Model | IC | RankIC | Ann Ret | Sharpe | MDD |
| :--- | :--- | :--- | :--- | :--- | :--- |
| LightGBM | 0.0625 | 0.0034 | 4.89% | 0.4051 | -27.68% |
| ALSTM | 0.0070 | 0.0132 | 1.59% | 0.0661 | -86.58% |

## Next Steps Plan

### Phase 1: LightGBM Strategy Optimization (Suggestion 1)
- **Signal Refinement**: Analyze the distribution of LightGBM predictions to set an optimal `signal_threshold`.
- **Dynamic Risk Control**: Re-enable and tune `take_profit` and `stop_loss` specifically for ETH volatility.
- **Circuit Breaker Tuning**: Adjust the `max_drawdown_limit` to prevent catastrophic losses while allowing for normal crypto volatility.
- **Leverage Testing**: Evaluate the impact of different leverage levels (1.0x to 3.0x) on the Sharpe ratio.

### Phase 2: Feature Engineering & Selection (Suggestion 2)
- **Feature Importance Analysis**: Extract and visualize feature importance from the best LightGBM model.
- **Dimensionality Reduction**: Prune features with low importance to reduce noise and training time.
- **Cross-Validation**: Implement rolling walk-forward cross-validation to ensure the model's stability across different market regimes (2021-2024).
- **Crypto-Specific Features**: Explore adding funding rate or correlation-based features (e.g., ETH-BTC beta).

---
*Created on: 2026-01-13*
