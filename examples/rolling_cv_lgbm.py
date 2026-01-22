import qlib
import pandas as pd
import numpy as np
import os
from qlib.utils import init_instance_by_config
from qlib.workflow import R
from qlib.data.dataset.handler import DataHandlerLP
from qlib.contrib.data.loader import Alpha158DL, Alpha360DL
from qlib.log import get_module_logger
from qlib.backtest import backtest as qlib_backtest

# ==============================================================================
# PARAMETERS
# ==============================================================================
SYMBOL = "eth_usdt_4h_future"
FREQ = "240min"
PROVIDER_URI = "data/qlib_data/crypto"

# Rolling CV Settings
TRAIN_WINDOW = 365 * 2 # 2 Years
VALID_WINDOW = 30 * 4  # 4 Months
TEST_WINDOW = 30 * 4   # 4 Months
STEP_SIZE = 30 * 4    # 4 Months

START_DATE = "2020-01-01"
END_DATE = "2026-01-01"

# ==============================================================================

def get_data_config(train_range, valid_range, test_range):
    f158, n158 = Alpha158DL.get_feature_config()
    f360, n360 = Alpha360DL.get_feature_config()
    
    custom_features = [
        "$high/$low - 1",
        "$close/$vwap - 1",
        "($close-Min($low, 10))/(Max($high, 10)-Min($low, 10)+1e-12)", # RSV 10
        "Sin(2 * 3.1415926 * Weekday($close) / 7)",
        "Cos(2 * 3.1415926 * Weekday($close) / 7)",
        "Sin(2 * 3.1415926 * Hour($close) / 24)",
        "Cos(2 * 3.1415926 * Hour($close) / 24)",
    ]
    custom_names = ["range", "vwap_dev", "rsv10", "weekday_sin", "weekday_cos", "hour_sin", "hour_cos"]

    hybrid_features = f158 + f360 + custom_features
    hybrid_names = [f"A158_{n}" for n in n158] + [f"A360_{n}" for n in n360] + custom_names
    label_cfg = ["(Ref($close, -3)/$close - 1) / (Std(Ref($close, -1)/$close - 1, 20) + 1e-6)"]

    handler_kwargs = {
        "class": "DataHandlerLP",
        "module_path": "qlib.data.dataset.handler",
        "kwargs": {
            "start_time": train_range[0], 
            "end_time": test_range[1],
            "instruments": [SYMBOL],
            "data_loader": {
                "class": "QlibDataLoader",
                "kwargs": {
                    "config": {
                        "feature": (hybrid_features, hybrid_names),
                        "label": (label_cfg, ["LABEL"]),
                    },
                    "freq": FREQ,
                }
            },
            "learn_processors": [
                {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "fit_start_time": train_range[0], "fit_end_time": train_range[1]}},
                {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
                {"class": "Fillna", "kwargs": {"fields_group": "label"}},
            ],
        }
    }

    dataset_conf = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": handler_kwargs,
            "segments": {
                "train": train_range,
                "valid": valid_range,
                "test": test_range,
            },
        },
    }
    return dataset_conf

def run_rolling_cv():
    logger = get_module_logger("rolling_cv")
    qlib.init(provider_uri=PROVIDER_URI, region=qlib.config.REG_CN)

    strategy_conf = {
        "class": "CryptoLongShortStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {
            "signal": "<PRED>",
            "direction": "long-short",
            "signal_threshold": 0.0,
            "leverage": 1.0,
            "take_profit": 0.15,
            "stop_loss": -0.07,
            "max_drawdown_limit": 1.0,
            "topk": 1,
        }
    }

    from qlib.data import D
    cal = D.calendar(freq=FREQ)
    max_date = pd.to_datetime(cal[-1])

    all_results = []
    current_test_start = pd.to_datetime(START_DATE) + pd.Timedelta(days=TRAIN_WINDOW + VALID_WINDOW)
    
    fold = 0
    while current_test_start < pd.to_datetime(END_DATE):
        fold += 1
        test_end = current_test_start + pd.Timedelta(days=TEST_WINDOW)
        if test_end > max_date:
            logger.info(f"Test end {test_end} exceeds max date {max_date}. Stopping.")
            break
            
        valid_start = current_test_start - pd.Timedelta(days=VALID_WINDOW)
        valid_end = current_test_start - pd.Timedelta(days=1)
        train_start = valid_start - pd.Timedelta(days=TRAIN_WINDOW)
        train_end = valid_start - pd.Timedelta(days=1)
        
        r_train = (train_start.strftime("%Y-%m-%d"), train_end.strftime("%Y-%m-%d"))
        r_valid = (valid_start.strftime("%Y-%m-%d"), valid_end.strftime("%Y-%m-%d"))
        r_test = (current_test_start.strftime("%Y-%m-%d"), test_end.strftime("%Y-%m-%d"))
        
        logger.info(f"--- FOLD {fold} ---")
        logger.info(f"Train: {r_train}, Valid: {r_valid}, Test: {r_test}")

        try:
            with R.start(experiment_name="rolling_cv_lgbm_v3"):
                R.set_tags(fold=fold)
                
                dataset_conf = get_data_config(r_train, r_valid, r_test)
                model_conf = {
                    "class": "LGBModel",
                    "module_path": "qlib.contrib.model.gbdt",
                    "kwargs": {
                        "objective": "regression", "learning_rate": 0.05,
                        "num_leaves": 128, "max_depth": 5, "subsample": 0.8,
                        "colsample_bytree": 0.8, "lambda_l2": 0.1, "num_threads": 8, "verbosity": -1,
                    },
                }
                
                model = init_instance_by_config(model_conf)
                dataset = init_instance_by_config(dataset_conf)
                model.fit(dataset)
                
                # Signal Generation
                pred = model.predict(dataset)
                pred_label = dataset.prepare("test", col_set=["label"], data_key=DataHandlerLP.DK_L)
                
                # Align they for overall correlation (Single Symbol IC)
                common_idx = pred.index.intersection(pred_label.index)
                s_pred = pred.loc[common_idx].values.flatten()
                s_label = pred_label.loc[common_idx].values.flatten()
                ic = np.corrcoef(s_pred, s_label)[0, 1] if len(s_pred) > 1 else 0
                
                # Backtest using direct method
                pred_df = pred.loc[common_idx]
                if isinstance(pred_df, pd.Series):
                    pred_df = pred_df.to_frame("score")
                
                # Pass the prediction dataframe directly to strategy
                fold_strategy = strategy_conf.copy()
                fold_strategy["kwargs"] = strategy_conf["kwargs"].copy()
                fold_strategy["kwargs"]["signal"] = pred_df
                
                executor_conf = {
                    "class": "SimulatorExecutor",
                    "module_path": "qlib.backtest.executor",
                    "kwargs": {"time_per_step": FREQ, "generate_portfolio_metrics": True}
                }
                
                portfolio_metric_dict, indicator_dict = qlib_backtest(
                    start_time=r_test[0], end_time=r_test[1],
                    strategy=fold_strategy, executor=executor_conf,
                    benchmark=None, exchange_kwargs={
                        "codes": [SYMBOL], "freq": FREQ, "limit_threshold": None,
                        "deal_price": "close", "open_cost": 0.0005, "close_cost": 0.0005,
                    }
                )
                
                report, _ = portfolio_metric_dict.get(FREQ)
                if report is not None and not report.empty:
                    ar = report['return'].mean() * 365 * 6 # Approx for 4H
                    vol = report['return'].std() * np.sqrt(365 * 6)
                    sharpe = ar / vol if vol > 0 else 0
                    mdd = ( (1+report['return']).cumprod() / (1+report['return']).cumprod().cummax() - 1).min()
                else:
                    ar, sharpe, mdd = 0, 0, 0
                
                fold_res = {
                    "fold": fold, "period": r_test[0], "ic": ic,
                    "ann_ret": ar, "sharpe": sharpe, "mdd": mdd
                }
                all_results.append(fold_res)
                print(f"Fold {fold} OK. IC: {ic:.4f}, Sharpe: {sharpe:.4f}, MDD: {mdd:.2%}")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Fold {fold} failed: {e}")
            
        current_test_start += pd.Timedelta(days=STEP_SIZE)

    if all_results:
        summary = pd.DataFrame(all_results)
        print("\n" + "="*80)
        print("ROLLING WALK-FORWARD CV SUMMARY (LightGBM)")
        print("="*80)
        print(summary.to_string(index=False))
        print("="*80)
        print(f"Average IC: {summary['ic'].mean():.4f}")
        print(f"Average Sharpe: {summary['sharpe'].mean():.4f}")
        summary.to_csv("docs/rolling_cv_lgbm_results_v3.csv", index=False)

if __name__ == "__main__":
    run_rolling_cv()
