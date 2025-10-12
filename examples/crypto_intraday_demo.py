"""
Minimal intraday demo using CryptoTopNStrategy (1h interval).

Notes:
- This demo expects that you have 1h (or higher-frequency) data available in qlib's provider_uri.
- If you don't have 1h data, the script will attempt to run but may fail when preparing dataset.
"""
import qlib
import runpy
from qlib.constant import REG_CN
from qlib.utils import init_instance_by_config, flatten_dict
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, PortAnaRecord, SigAnaRecord
from qlib.tests.data import GetData
from qlib.contrib.strategy import CryptoTopNStrategy
from qlib.data import D
import os

# optional: use collector to download crypto data (daily) and normalize into provider_uri
try:
    import scripts.data_collector.crypto.collector as cc
except Exception:
    cc = None


def main():
    # use a separate provider dir for crypto daily data
    provider_uri = "../data/crypto_1d"

    # Attempt to download & normalize crypto daily data using the provided collector (best-effort)
    if cc is not None:
        try:
            print("Starting crypto data download/normalize (1d) into:", provider_uri)
            # source dir for raw csvs
            source_dir = "../data/crypto_1d/source"
            start = "2018-01-01"
            end = None
            limit_nums = 10  # limit to 10 symbols for quick demo

            collector = cc.CryptoCollector1d(save_dir=source_dir, start=start, end=end, interval="1d", max_workers=2, max_collector_count=2, delay=1, limit_nums=limit_nums)
            collector.collector_data()

            # normalize into provider_uri using Normalize helper
            normalize_obj = cc.Normalize(source_dir, provider_uri, cc.CryptoNormalize1d, max_workers=2)
            normalize_obj.normalize()

            print("Crypto data download/normalize finished (or attempted)")
        except Exception as e:
            print("Crypto data retrieval failed or skipped:", e)
    else:
        print("Crypto collector not importable; skipping download step. Make sure to run scripts/data_collector/crypto/collector.py separately if needed.")

    # qlib init using the crypto provider uri
    try:
        qlib.init(provider_uri=provider_uri, region=REG_CN)
    except Exception as e:
        print("qlib.init failed with provider_uri=", provider_uri, " error:", e)
        # fallback: try default data fetch for tests
        provider_uri = "../data/cn_data"
        GetData().qlib_data(target_dir=provider_uri, region=REG_CN, exists_skip=True)
        qlib.init(provider_uri=provider_uri, region=REG_CN)

    # Build an intraday signal from available 1h crypto data in the provider.
    # If no intraday data is available or any error occurs, fall back to the synthetic demo.
    try:
        instruments = D.list_instruments(None, start_time=None, end_time=None, freq="1h", as_list=True)
        if not instruments:
            raise RuntimeError("no intraday instruments found in provider")

        universe = instruments[:50]

        import pandas as _pd

        end = None
        start = _pd.Timestamp.now() - _pd.Timedelta(days=7)

        price_feat = D.features(universe, ["$close"], start, end, freq="1h", disk_cache=1)
        # normalize price_feat to a Series of close prices indexed by (instrument, datetime)
        if isinstance(price_feat, _pd.DataFrame) and "$close" in price_feat.columns:
            s = price_feat["$close"]
        elif isinstance(price_feat, _pd.Series):
            s = price_feat
        else:
            # try to extract first column
            s = price_feat.iloc[:, 0]

        price_wide = s.unstack(level=0)
        # next-period return as the signal (oracle-like for testing)
        ret = price_wide.pct_change().shift(-1)
        pred_series = ret.stack()
        # make sure index is (instrument, datetime)
        try:
            pred_series = pred_series.swaplevel(0, 1).sort_index()
        except Exception:
            pred_series = pred_series.sort_index()

        # prepare port_analysis_config using CryptoTopNStrategy with the precomputed signal
        port_analysis_config = {
            "executor": {"class": "SimulatorExecutor", "module_path": "qlib.backtest.executor", "kwargs": {"time_per_step": "1h", "generate_portfolio_metrics": True}},
            "strategy": {
                "class": "CryptoTopNStrategy",
                "module_path": "qlib.contrib.strategy.crypto_strategy",
                "kwargs": {
                    "signal": pred_series,
                    "universe": universe,
                    "top_n": 3,
                    "max_leverage": 3.0,
                    "sizing": "equal_dollar",
                    "vol_lookback": 20,
                    "only_tradable": True,
                },
            },
            "backtest": {"start_time": str(pred_series.index.get_level_values(1).min()), "end_time": str(pred_series.index.get_level_values(1).max()), "account": 100000, "benchmark": None, "exchange_kwargs": {"freq": "1h", "limit_threshold": 0.095, "deal_price": "close", "open_cost": 0.0005, "close_cost": 0.0005, "min_cost": 1}},
        }
    except Exception as e:
        print("Could not construct intraday signal from provider (fallback to synthetic). Reason:", e)
        runpy.run_path(os.path.join(os.path.dirname(__file__), "crypto_intraday_synth_run.py"), run_name="__main__")
        return

    try:
        example_df = dataset.prepare("train")
        print(example_df.head())
    except Exception as e:
        print("Warning: dataset.prepare failed. Make sure you have intraday data available. Error:", e)

    with R.start(experiment_name="crypto_intraday_demo"):
        R.log_params(strategy=str(strategy.__class__.__name__))
        try:
            model.fit(dataset)
        except Exception:
            print("Model fit failed or is no-op in demo; continuing to prediction step")

        recorder = R.get_recorder()
        sr = SignalRecord(model, dataset, recorder)
        try:
            sr.generate()
        except Exception as e:
            print("Signal generation failed:", e)

        sar = SigAnaRecord(recorder)
        try:
            sar.generate()
        except Exception:
            print("Signal analysis failed or no signals generated")

        par = PortAnaRecord(recorder, port_analysis_config, "1h")
        try:
            par.generate()
        except Exception as e:
            print("Backtest failed (likely due to missing intraday data or exchange implementation):", e)


if __name__ == "__main__":
    main()
