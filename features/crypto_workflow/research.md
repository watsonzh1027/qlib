# research.md — Crypto workflow technical decisions

## Decisions (summary)
1. Data source: ccxt + OKX
   - Decision: 使用 ccxt 的 OKX connector 拉取 OHLCV（timestamp, open, high, low, close, volume）。
   - Rationale: ccxt 提供统一接口，可直接支持 OKX 并容易迁移到其他交易所。
   - Alternatives: 继续用 CoinGecko（不满足高频/分时精度需求）、使用交易所官方 SDK（增加维护成本）。

2. Storage format:
   - Decision: 优先使用 Parquet（列式、压缩、读取快），退回到压缩 CSV 作为兼容选项。
   - Rationale: Parquet 在大数据量下效率更高，便于按列读取特征。

3. Model:
   - Decision: 使用 LightGBM（LGBModel）作为首选模型框架。
   - Rationale: 轻量、训练速度快、对表格特征表现良好，且易序列化与部署。
   - Alternatives: XGBoost、CatBoost（可选，留作 future work）。

4. Model serialization:
   - Decision: 使用 LightGBM 自带的 model.save_model / model.load_model 或 joblib 保存 wrapper。
   - Rationale: 与训练框架兼容，跨平台恢复简单。

5. Backtest assumptions:
   - Transaction cost: configurable per-pair (默认 0.0005)
   - Slippage: fixed percent or per-fill spread (configurable)
   - Execution: assume market orders filled at next candle open (documented in quickstart)

## NEEDS CLARIFICATION (if any)
- Q1: 需要支持哪些时间粒度？（建议：1m, 5m, 1h, 1d）  
  Suggested default: 1m, 5m, 1h

## Next steps
- Implement ETL pipeline using ccxt fetch_ohlcv → normalize → write parquet.
- Implement trainer module wrapping LightGBM, model persistence and basic eval report.
- Implement predictor + signal-rule module and backtest harness.
