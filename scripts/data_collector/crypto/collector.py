import abc
import sys
import os
import datetime

# Disable Fire pager globally to ensure help stays in the terminal
os.environ["FIRE_PAGER"] = "cat"
os.environ["FIRE_USE_PAGER"] = "0"
from pathlib import Path

import fire
import pandas as pd
from loguru import logger
from dateutil.tz import tzlocal

CUR_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(CUR_DIR)) # For BaseRun's importlib.import_module("collector")
from data_collector.base import BaseCollector, BaseNormalize, BaseRun
from data_collector.utils import deco_retry
from qlib.utils import code_to_fname
from scripts.symbol_utils import normalize_symbols_list, get_data_path, normalize_symbol as norm_sym, get_ccxt_symbol

import ccxt
from time import mktime
from datetime import datetime as dt
import time
import json
from scripts.config_manager import ConfigManager

# Configure logging
LOG_DIR = CUR_DIR.parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(LOG_DIR / "crypto_collector.log", rotation="10 MB")


_CG_CRYPTO_SYMBOLS = None


def get_cg_crypto_symbols(qlib_data_path: [str, Path] = None, symbol_file: str = None) -> list:
    """get crypto symbols in okx
    
    Returns
    -------
        crypto symbols in given exchanges list of okx
    """
    global _CG_CRYPTO_SYMBOLS  # pylint: disable=W0603

    @deco_retry
    def _get_coingecko():
        try:
            cg = ccxt.okx()
            _symbols = list(cg.load_markets().keys())
        except Exception as e:
            raise ValueError("request error") from e
        return _symbols

    if _CG_CRYPTO_SYMBOLS is None:
        if symbol_file:
            try:
                with open(symbol_file, 'r') as f:
                    if symbol_file.endswith('.json'):
                         data = json.load(f)
                         _all_symbols = data.get('symbols', []) if isinstance(data, dict) else data
                    else:
                        _all_symbols = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.warning(f"Failed to load symbols from {symbol_file}: {e}")
                _all_symbols = _get_coingecko()
        else:
            _all_symbols = _get_coingecko()

        _CG_CRYPTO_SYMBOLS = normalize_symbols_list(sorted(set(_all_symbols)))

    return _CG_CRYPTO_SYMBOLS


class CryptoCollector(BaseCollector):
    def __init__(
        self,
        save_dir: [str, Path],
        start=None,
        end=None,
        interval="1d",
        max_workers=1,
        max_collector_count=2,
        delay=1,  # delay need to be one
        check_data_length: int = None,
        limit_nums: int = None,
        symbol_file: str = None,
        market_type="spot",
        limit=100,
    ):
        """

        Parameters
        ----------
        save_dir: str
            crypto save dir
        max_workers: int
            workers, default 4
        max_collector_count: int
            default 2
        delay: float
            time.sleep(delay), default 0
        interval: str
            freq, value from [1min, 5min, 15min, 30min, 1h, 4h, 1d, 1w], default 1d
        start: str
            start datetime, default None
        end: str
            end datetime, default None
        check_data_length: int
            check data length, if not None and greater than 0, each symbol will be considered complete if its data length is greater than or equal to this value, otherwise it will be fetched again, the maximum number of fetches being (max_collector_count). By default None.
        limit_nums: int
            using for debug, by default None
        market_type: str
            market type, from [spot, future, swap], default spot
        limit: int
            limit of fetch_ohlcv
        """
        self.symbol_file = symbol_file
        self.market_type = market_type
        self.limit = limit
        # BaseCollector.__init__ calls normalize_start_datetime/normalize_end_datetime
        # so we must ensure they are robust to different intervals.
        super(CryptoCollector, self).__init__(
            save_dir=save_dir,
            start=start,
            end=end,
            interval=interval,
            max_workers=max_workers,
            max_collector_count=max_collector_count,
            delay=delay,
            check_data_length=check_data_length,
            limit_nums=limit_nums,
        )

        self.init_datetime()

    def normalize_start_datetime(self, start_datetime: [str, pd.Timestamp] = None):
        if start_datetime:
            return pd.Timestamp(str(start_datetime))
        # Fallback to a default if getattr fails (which it will for new intervals)
        attr_name = f"DEFAULT_START_DATETIME_{self.interval.upper()}"
        return getattr(self, attr_name, pd.Timestamp("2020-01-01"))

    def normalize_end_datetime(self, end_datetime: [str, pd.Timestamp] = None):
        if end_datetime:
            return pd.Timestamp(str(end_datetime))
        attr_name = f"DEFAULT_END_DATETIME_{self.interval.upper()}"
        return getattr(self, attr_name, pd.Timestamp(datetime.datetime.now() + pd.Timedelta(days=1)).date())

    def init_datetime(self):
        # Broaden interval check
        valid_intervals = ["1min", "5min", "15min", "30min", "1h", "4h", "1d", "1w"]
        if self.interval not in valid_intervals:
             logger.warning(f"Unrecognized interval: {self.interval}. Use at your own risk.")

        self.start_datetime = self.convert_datetime(self.start_datetime, self._timezone)
        self.end_datetime = self.convert_datetime(self.end_datetime, self._timezone)

    @staticmethod
    def convert_datetime(dt: [pd.Timestamp, datetime.date, str], timezone):
        try:
            dt = pd.Timestamp(dt, tz=timezone).timestamp()
            dt = pd.Timestamp(dt, tz=tzlocal(), unit="s")
        except ValueError as e:
            pass
        return dt

    @property
    def _timezone(self):
        return "Asia/Shanghai"

    def get_instrument_list(self):
        logger.info("get okx crypto symbols......")
        symbols = get_cg_crypto_symbols(symbol_file=self.symbol_file)
        
        # Rewrite hierarchical symbols to match current collection parameters
        # This prevents confusion like showing /240min/ when /1h/ is requested
        aligned_symbols = []
        for s in symbols:
            parts = s.split('/')
            if len(parts) == 3:
                # Update interval and market_type to match current Run instance
                parts[1] = self.interval
                parts[2] = self.market_type.upper()
                aligned_symbols.append('/'.join(parts))
            else:
                aligned_symbols.append(s)
        
        symbols = sorted(set(aligned_symbols))
        logger.info(f"get {len(symbols)} symbols.")
        return symbols

    def normalize_symbol(self, symbol):
        return norm_sym(symbol.split('/')[0])

    def save_instrument(self, symbol, df: pd.DataFrame):
        """save instrument data to file with hierarchical directory structure"""
        symbol = self.normalize_symbol(symbol)
        if df is None or df.empty:
            logger.warning(f"{symbol} is empty")
            return

        # 1. Generate path using the hierarchical naming convention
        # Root is self.save_dir
        instrument_path = Path(get_data_path(str(self.save_dir), symbol, self.interval, self.market_type))
        instrument_path.parent.mkdir(parents=True, exist_ok=True)

        # 2. Set 'symbol' column to a clean format (e.g., BTC_USDT)
        clean_symbol = norm_sym(symbol)
        df["symbol"] = clean_symbol

        # 3. Remove redundant 'timestamp' if 'date' is present
        if "timestamp" in df.columns and "date" in df.columns:
            df = df.drop(columns=["timestamp"])

        # 4. Reorder columns: 'date' first, then 'symbol', then OHLCV
        cols = ["date", "symbol"] + [c for c in df.columns if c not in ["date", "symbol"]]
        df = df[cols]

        # 5. Handle existing data and deduplicate
        if instrument_path.exists():
            try:
                _old_df = pd.read_csv(instrument_path)
                df = pd.concat([_old_df, df], sort=False)
                df = df.drop_duplicates(subset=["date"], keep="last")
            except Exception as e:
                logger.warning(f"Failed to merge with existing data for {symbol}: {e}")

        # 6. Final reorder to guarantee 'date' is the first column and 'symbol' is second
        cols = ["date", "symbol"] + [c for c in df.columns if c not in ["date", "symbol"]]
        df = df[cols]

        # 7. Save to CSV
        df.to_csv(instrument_path, index=False)
        logger.debug(f"Saved {symbol} to {instrument_path}")

    @staticmethod
    def get_data_from_remote(symbol, interval, start, end, market_type="spot", limit=100):
        logger.info(f"Downloading {symbol} ({interval}, {market_type})...")
        error_msg = f"{symbol}-{interval}-{start}-{end}"
        try:
            # Map interval to CCXT timeframe
            timeframe_map = {
                "1min": "1m",
                "5min": "5m",
                "15min": "15m",
                "30min": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d",
                "1w": "1w",
            }
            timeframe = timeframe_map.get(interval, interval)
            
            # Use market_type in options
            cg = ccxt.okx({'options': {'defaultType': market_type}})
            ccxt_symbol = get_ccxt_symbol(symbol)
            
            start_ts = int(pd.Timestamp(start).timestamp() * 1000)
            end_ts = int(pd.Timestamp(end).timestamp() * 1000)
            
            all_data = []
            since = start_ts
            
            while since < end_ts:
                ohlcv = cg.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, since=since, limit=limit, params={'endTime': end_ts})
                if not ohlcv:
                    if not all_data:
                        # If no data found yet, 'since' might be before listing. 
                        # Jump forward 180 days (approx 6 months) to search for the start of history faster.
                        last_since = since
                        since += 180 * 24 * 60 * 60 * 1000
                        logger.debug(f"No data for {symbol} at {pd.to_datetime(last_since, unit='ms')}, jumping to {pd.to_datetime(since, unit='ms')}...")
                        if since >= end_ts:
                            break
                        continue
                    else:
                        break
                all_data.extend(ohlcv)
                # update since
                last_ts = ohlcv[-1][0]
                if last_ts >= since:
                    since = last_ts + 1
                else:
                    break
                time.sleep(cg.rateLimit / 1000.0)

            if all_data:
                _resp = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                # CCXT timestamps are in UTC
                _resp["date"] = pd.to_datetime(_resp["timestamp"], unit="ms", utc=True)
                
                # Ensure start/end are also UTC Timestamps for comparison
                start_dt = pd.to_datetime(start, utc=True)
                end_dt = pd.to_datetime(end, utc=True)
                
                _resp = _resp[(_resp["date"] <= end_dt) & (_resp["date"] >= start_dt)]
                if interval == "1d":
                    _resp["date"] = [x.date() for x in _resp["date"]]
                else:
                    _resp["date"] = [x.strftime("%Y-%m-%d %H:%M:%S") for x in _resp["date"]]
                _resp = _resp.drop(columns=['timestamp'])
                if _resp.shape[0] != 0:
                    # Typical Price formula as VWAP proxy
                    _resp["vwap"] = (_resp["high"] + _resp["low"] + _resp["close"]) / 3.0
                    # Convert volume to USDT value (scaled by 1000) for cross-symbol comparability
                    _resp["volume"] = (_resp["vwap"] * _resp["volume"]) / 1000.0
                    return _resp.reset_index(drop=True)
        except Exception as e:
            logger.warning(f"{error_msg}:{e}")

    def get_data(
        self, symbol: str, interval: str, start_datetime: pd.Timestamp, end_datetime: pd.Timestamp
    ) -> pd.DataFrame:
        """
        Fetch data for the given symbol and interval. 
        """
        self.sleep()
        return self.get_data_from_remote(
            symbol,
            interval=interval,
            start=start_datetime,
            end=end_datetime,
            market_type=self.market_type,
            limit=self.limit,
        )


# Keep these for backward compatibility
#CryptoCollector1d = CryptoCollector
#CryptoCollector1h = CryptoCollector
#CryptoCollector1min = CryptoCollector


class CryptoNormalize(BaseNormalize):
    DAILY_FORMAT = "%Y-%m-%d"

    @staticmethod
    def normalize_crypto(
        df: pd.DataFrame,
        calendar_list: list = None,
        date_field_name: str = "date",
        symbol_field_name: str = "symbol",
    ):
        if df.empty:
            return df
        df = df.copy()
        df.set_index(date_field_name, inplace=True)
        df.index = pd.to_datetime(df.index)
        df = df[~df.index.duplicated(keep="first")]
        if calendar_list is not None:
            df = df.reindex(
                pd.DataFrame(index=calendar_list)
                .loc[
                    pd.Timestamp(df.index.min()).date() : pd.Timestamp(df.index.max()).date()
                    + pd.Timedelta(hours=23, minutes=59)
                ]
                .index
            )
        df.sort_index(inplace=True)

        df.index.names = [date_field_name]
        return df.reset_index()

    def _get_calendar_list(self):
        return None

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.normalize_crypto(df, self._calendar_list, self._date_field_name, self._symbol_field_name)
        return df


# Keep these for backward compatibility
CryptoNormalize1d = CryptoNormalize
CryptoNormalize1h = CryptoNormalize
CryptoNormalize1min = CryptoNormalize


class Run:
    def __init__(self, source_dir=None, normalize_dir=None, max_workers=1, interval="1d", config_path="config/workflow.json", limit=None, market_type=None):
        """
        Crypto Data Collector CLI.

        Unified Command Interface:
          python collector.py [FLAGS] COMMAND

        COMMANDS:
          download    Download raw OHLCV data from exchange (supports increments).
          normalize   Process raw CSV files into Qlib-formatted files.

        FLAGS (Configuration):
          --config_path   Path to workflow.json (default: config/workflow.json)
          --source_dir    The directory where the raw data is saved.
          --normalize_dir Directory for normalize data.
          --max_workers   Concurrent number (default: 1).
          --interval      Frequency (1min, 1h, 1d, etc.)
          --limit         Batch size for CCXT fetch_ohlcv (default: 100).
          --market_type   'spot' or 'future' (default: 'spot').
        """
        self._source_dir_arg = source_dir
        self._normalize_dir_arg = normalize_dir
        self._max_workers_arg = max_workers
        self._interval_arg = interval
        self._limit_arg = limit
        self._market_type_arg = market_type
        self.config_path = config_path
        self._prepared = False

    def _prepare_conf(self):
        if self._prepared:
            return
        self._config_manager = ConfigManager(self.config_path)
        config = self._config_manager.load_config()

        # Resolve source_dir
        self.source_dir = self._source_dir_arg
        if self.source_dir is None:
            self.source_dir = config.get("data", {}).get("csv_data_dir") or config.get("data_dir", "data/klines")
        self.source_dir = Path(self.source_dir).expanduser().resolve()
        self.source_dir.mkdir(parents=True, exist_ok=True)

        # Resolve normalize_dir
        self.normalize_dir = self._normalize_dir_arg
        if self.normalize_dir is None:
            self.normalize_dir = config.get("data", {}).get("normalize_dir") or "data/normalize"
        self.normalize_dir = Path(self.normalize_dir).expanduser().resolve()
        self.normalize_dir.mkdir(parents=True, exist_ok=True)

        self.market_type = self._market_type_arg
        if self.market_type is None:
            self.market_type = config.get("data", {}).get("market_type", "spot")

        self.limit = self._limit_arg
        if self.limit is None:
            self.limit = config.get("data_collection", {}).get("limit", 100)

        # Resolve interval
        self.interval = self._interval_arg
        if self.interval == "1d": 
             cfg_interval = config.get("data_collection", {}).get("interval", "1d")
             self.interval = "1min" if cfg_interval == "1m" else cfg_interval
             
        self.max_workers = self._max_workers_arg
        self._prepared = True

    @property
    def collector_class_name(self):
        return "CryptoCollector"

    @property
    def normalize_class_name(self):
        return "CryptoNormalize"

    @property
    def default_base_dir(self) -> Path:
        return CUR_DIR

    def download(
        self,
        max_collector_count=2,
        delay=0,
        start=None,
        end=None,
        check_data_length: int = None,
        limit_nums=None,
        symbol_file=None,
    ):
        """download data from Internet"""
        self._prepare_conf()
        if start is None:
            start = self._config_manager.get_with_defaults("data_collection", "start_time", "2020-01-01")
        if end is None:
            end = self._config_manager.get("data_collection", "end_time") or pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

        if symbol_file is None:
            symbol_file = self._config_manager.get("data", "symbols")
            if symbol_file:
                 full_path = Path(self._config_manager.config_path).parent.parent / symbol_file
                 symbol_file = str(full_path) if full_path.exists() else None

        CryptoCollector(
            self.source_dir,
            max_workers=self.max_workers,
            max_collector_count=max_collector_count,
            delay=delay,
            start=start,
            end=end,
            interval=self.interval,
            check_data_length=check_data_length,
            limit_nums=limit_nums,
            symbol_file=symbol_file,
            market_type=self.market_type,
            limit=self.limit,
        ).collector_data()

        print("\n" + "=" * 80)
        print("Data collection complete. Next steps:")
        print("=" * 80)
        # Suggest the generic batch command instead of per-symbol instructions
        print("1. Fetch and merge funding rates (Batch Process):")
        print(f"   python scripts/fetch_funding_rates.py --all --config {self.config_path}")
        
        print("\n2. Normalize data:")
        print(f"   python scripts/data_collector/crypto/collector.py normalize -c {self.config_path}")
        print("\n3. Dump to Qlib binary format:")
        print(f"   python scripts/dump_bin.py dump_all --data_path {self.normalize_dir} --qlib_dir data/qlib_data/crypto --freq {self.interval} --date_field_name date")
        print("=" * 80 + "\n")

    def normalize(self, date_field_name: str = "date", symbol_field_name: str = "symbol", **kwargs):
        """normalize data"""
        self._prepare_conf()
        from data_collector.base import Normalize
        yc = Normalize(
            source_dir=self.source_dir,
            target_dir=self.normalize_dir,
            normalize_class=CryptoNormalize,
            max_workers=self.max_workers,
            date_field_name=date_field_name,
            symbol_field_name=symbol_field_name,
            **kwargs,
        )
        yc.normalize()

        qlib_dir = self._config_manager.get("data", "bin_data_dir") or "data/qlib_data/crypto"

        print("\n" + "=" * 80)
        print("Normalization complete. Next steps:")
        print("=" * 80)
        print("1. Dump to Qlib binary format:")
        print(f"   python scripts/dump_bin.py dump_all --data_path {self.normalize_dir} --qlib_dir {qlib_dir} --freq {self.interval} --date_field_name date")
        print("\n2. Tune Hyperparameters (Optional):")
        print(f"   python scripts/tune_hyperparameters.py")
        print("\n3. Train Sample Model:")
        print(f"   python scripts/train_sample_model.py")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    # Custom help for the base cases to ensure it stays on screen and is accurate
    if len(sys.argv) == 1 or sys.argv[1] in ["--help", "-h"]:
        help_text = """
NAME
    collector.py - Crypto Data Collector CLI.

SYNOPSIS
    python collector.py COMMAND [FLAGS]

COMMANDS
    download    Download raw OHLCV data from exchange (supports increments).
    normalize   Process raw CSV files into Qlib-formatted files.

FLAGS (Global Configuration):
    -c, --config_path   Path to workflow.json (default: config/workflow.json)
    -s, --source_dir    The directory where raw CSV data is stored.
    -n, --normalize_dir The directory for Qlib-normalized data.
    -m, --max_workers   Number of parallel processes (default: 1).
    -i, --interval      Frequency of data (e.g., 1min, 1h, 1d).

Examples:
    python collector.py download -i 1h
    python collector.py normalize -c config/workflow.json
"""
        print(help_text)
        sys.exit(0)
        
    # Use class for proper global flag parsing and help inheritance
    fire.Fire(Run)
