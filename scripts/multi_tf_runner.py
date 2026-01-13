import os
import subprocess
import argparse
from loguru import logger
from concurrent.futures import ProcessPoolExecutor, as_completed

def run_experiment(symbol, freq, n_trials, vol_scale, train_start, n_jobs=2):
    logger.info(f"Starting {symbol} | Freq: {freq} | Start: {train_start} | Vol Scale: {vol_scale}")
    
    cmd = [
        "python", "examples/model_test.py",
        "--symbol", symbol,
        "--freq", freq,
        "--n_trials", str(n_trials),
        "--n_jobs", str(n_jobs),
        "--train_start", train_start
    ]
    if vol_scale:
        cmd.append("--vol_scale")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    output = result.stdout + "\n" + result.stderr
    report_start = output.find("FINAL MODEL EVALUATION REPORT")
    if report_start != -1:
        report_end = output.find("===", report_start + 200)
        report = output[report_start : report_end + 50] if report_end != -1 else output[report_start:]
        logger.success(f"Finished {symbol} at {freq}")
        return report
    
    logger.error(f"Failed {symbol} at {freq}. Check logs/qlib-model_test-*.log")
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_trials", type=int, default=5)
    parser.add_argument("--max_workers", type=int, default=3)
    args = parser.parse_args()

    # Timeframe balancing logic:
    # 1d: since 2020-01-01 (~2100 bars)
    # 4h: since 2023-10-01 (~5000 bars)
    # 1h: since 2025-01-01 (~9000 bars)
    timeframes = [
        {"symbol": "ETH_USDT_1H_FUTURE", "freq": "60min", "start": "2024-01-01"},
        {"symbol": "ETH_USDT_4H_FUTURE", "freq": "240min", "start": "2023-01-01"},
        {"symbol": "ETH_USDT_1D_FUTURE", "freq": "day", "start": "2020-01-01"},
    ]

    all_tasks = []
    for item in timeframes:
        for vol_scale in [False, True]:
            all_tasks.append((item["symbol"], item["freq"], args.n_trials, vol_scale, item["start"]))

    all_reports = []
    logger.info(f"Balanced Parallel Experiments | Workers: {args.max_workers}")
    
    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_task = {
            executor.submit(run_experiment, *task, n_jobs=2): task 
            for task in all_tasks
        }
        
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                report = future.result()
                if report:
                    all_reports.append(report)
            except Exception as e:
                logger.error(f"Task {task} generated an exception: {e}")

    # Save summary
    with open("docs/multi_tf_results.txt", "w") as f:
        f.write("\n\n".join(all_reports))
    
    logger.info(f"All experiments completed. Results: {len(all_reports)}/{len(all_tasks)}. Summary saved to docs/multi_tf_results.txt")

if __name__ == "__main__":
    main()
