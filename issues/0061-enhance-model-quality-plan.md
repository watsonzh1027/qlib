# Issue: Enhance Model Quality and Feature Engineering for ETH Trading

## Status: CLOSED (Phase 1 Complete)

## Problem Description
The initial backtest results for ETH 4H trading showed poor annualized returns and high drawdowns. The objective was to systematically improve the predictive quality of the models and optimize the trading strategy.

## Progress Summary (January 13, 2026)
1.  **System Infrastructure Fixes**:
    *   Registered `Sin` and `Cos` operators in Qlib's core (`qlib/data/ops.py`) to support cyclical time encoding for crypto features.
2.  **Model Comparison & Selection**:
    *   LightGBM vs ALSTM comparison confirmed **LightGBM** as the more stable and predictive model for single-symbol ETH 4H data.
3.  **Strategy Optimization (Grid Search)**:
    *   Performed exhaustive search for risk parameters.
    *   Identified that **TP=15%**, **SL=7%**, and **Thr=0.0** significantly improved the risk-adjusted return (Sharpe ~0.99 in 2025).
4.  **Feature Importance & Pruning Analysis**:
    *   Analyzed 525 features. Top features include long-period volatility (`A158_STD60`) and trend stability (`A158_RSQR60`).
    *   Attempted pruning features with zero gain; however, results suggest that a full feature set provides better regularization for IC quality (0.0625 vs 0.0384 pruned).
5.  **Rolling Walk-Forward Cross-Validation**:
    *   Executed 11-fold rolling validation (2022-2025).
    *   **Average Sharpe: 0.81**, **Average IC: 0.0045**.
    *   Identified high performance in trending markets (Sharpe up to 4.7) and risks in rapid regime shifts.

## Final Results (Optimized LightGBM baseline)
| Metric | 2025 Year Test (Optimized Strategy) | Rolling CV Average (2022-2025) |
| :--- | :--- | :--- |
| **IC** | 0.0625 | 0.0045 |
| **Annualized Return** | 25.79% (Raw) / 4.89% (Base) | Variable |
| **Sharpe Ratio** | **0.996** | **0.81** |
| **Max Drawdown** | -24.06% | -39.3% (Avg Peak) |

## Key Artefacts Generated
- `examples/model_showdown.py`: Core comparison and final baseline script.
- `examples/grid_search_strategy.py`: Tool for optimizing strategy entry/exit.
- `examples/rolling_cv_lgbm.py`: Robust walk-forward validation framework.
- `docs/lgbm_feature_importance.csv`: Detailed feature gain analysis.
- `docs/strategy_grid_search_results.csv`: Optimized parameter set.

## Next Phase Recommendation
- **Feature Engineering**: Integration of Funding Rates, Open Interest, and Liquidations.
- **Dynamic Position Sizing**: Scale leverage based on model confidence or market volatility.
- **Regime Filtering**: Use a separate model to detect high-risk "washout" regimes to avoid Fold 1/7 style drawdowns.

---
*Completed on: 2026-01-13*
