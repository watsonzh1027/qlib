# Design: Crypto Data Feeder Module (change 0001)

## Overview

The Crypto Data Feeder Module is designed to automate the collection, storage, and conversion of cryptocurrency data from the OKX exchange for quantitative strategy research using the Qlib framework. It addresses the need for a reliable, scalable, and efficient data pipeline that can handle real-time data and integrate seamlessly with existing research workflows.

## Components
- **Top-50 selector (`scripts/get_top50.py`)**
  - Fetches funding rates via CCXT REST API.
  - Ranks symbols by absolute funding rate and persists the top 50 as JSON.

- **Data collector (`scripts/okx_data_collector.py`)**
  - Asynchronously collects data using ccxtpro and a cryptofeed-compatible approach.
  - Buffers 15-minute OHLCV data and periodic funding rate updates.
  - Exposes the `update_latest_data(symbols=None)` method for on-demand data fetching.

- **Storage layer (`openspec/utils/storage.py` / `okx_data/`)**
  - Stores data in Parquet file format, partitioned by date and symbol.
  - Each file's schema includes symbol, timestamp (in Unix seconds), open, high, low, close, volume, and interval.

- **Converter (`scripts/convert_to_qlib.py`)**
  - Merges and deduplicates data, producing Qlib-compatible instruments and binary feature files.

- **Backtest script (`scripts/sample_backtest.py`)**
  - Loads parameters dynamically using `ConfigManager`.
  - Reads `config/workflow.json` for centralized parameter management.
  - Ensures compatibility with the Qlib framework for crypto data.

## Data Flow and Failure Modes
- The `get_top50` script runs every 8 hours, updating the `top50_symbols.json` file.
- The data collector reads the `top50_symbols.json` file to determine which symbols to collect.
- Collected data is persisted in Parquet format, with the option for on-demand updates to append or merge the latest data rows.
- The system is designed to auto-reconnect and apply exponential backoff in case of websocket or connection errors.
- A graceful shutdown procedure is implemented to flush in-memory buffers to Parquet files, ensuring no data loss.

## Operational notes
- The module should be managed using `systemd` or `supervisor`, with logs directed to rotating files to manage disk usage.
- Daily conversion processes should be validated through automated tests, and smoke tests should be run using the Qlib data loader to ensure compatibility and correctness.

## Interfaces (short)
- `get_okx_funding_top50() -> List[str]`: Returns a list of the top 50 OKX perpetual swap symbols ranked by funding rate.
- `update_latest_data(symbols: Optional[List[str]]) -> Dict[str, pd.DataFrame]`: Fetches the latest 15-minute candles for the specified symbols (or all top 50 if none are specified), updates the local Parquet files, and returns the data for immediate use.
- `convert_to_qlib(output_dir: str) -> None`: Converts the collected data in Parquet format to Qlib's binary feature format, storing the results in the specified output directory.

- **Module Updates**:
  - `scripts/get_top50.py`: Adjust to align with the updated data flow and centralized parameter management.
  - `scripts/okx_data_collector.py`: Modify to ensure compatibility with the revised data storage schema.
  - `scripts/convert_to_qlib.py`: Update to handle new data formats and ensure seamless Qlib integration.
  - `scripts/sample_backtest.py`: Refactor to incorporate centralized parameter management and validate end-to-end functionality.