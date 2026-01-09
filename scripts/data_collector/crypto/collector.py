import abc
import sys
import datetime
from pathlib import Path

import fire
import pandas as pd
from loguru import logger
from dateutil.tz import tzlocal

CUR_DIR = Path(__file__).resolve().parent
sys.path.append(str(CUR_DIR))
sys.path.append(str(CUR_DIR.parent.parent))
from data_collector.base import BaseCollector, BaseNormalize, BaseRun
from data_collector.utils import deco_retry
from qlib.utils import code_to_fname
from scripts.symbol_utils import normalize_symbols_list

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
        logger.info(f"get {len(symbols)} symbols.")
        return symbols

    def normalize_symbol(self, symbol):
        sym = symbol.replace("/", "_")
        return f"{sym}_{self.interval}_{self.market_type}"

    def save_instrument(self, symbol, df: pd.DataFrame):
        """save instrument data to file with custom formatting"""
        if df is None or df.empty:
            logger.warning(f"{symbol} is empty")
            return

        # 1. Generate filename using the custom naming convention
        filename_base = self.normalize_symbol(symbol)
        filename_base = code_to_fname(filename_base)
        instrument_path = self.save_dir.joinpath(f"{filename_base}.csv")

        # 2. Set 'symbol' column to a clean format (e.g., BTC_USDT)
        clean_symbol = symbol.replace("/", "_")
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
            
            start_ts = int(pd.Timestamp(start).timestamp() * 1000)
            end_ts = int(pd.Timestamp(end).timestamp() * 1000)
            
            all_data = []
            since = start_ts
            
            while since < end_ts:
                ohlcv = cg.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
                if not ohlcv:
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
                    # Calculate VWAP as proxy if not provided
                    _resp["vwap"] = (_resp["open"] + _resp["high"] + _resp["low"] + _resp["close"]) / 4
                    # Convert volume to USDT value (scaled by 1000) for cross-symbol comparability
                    _resp["volume"] = (_resp["vwap"] * _resp["volume"]) / 1000.0
                    return _resp.reset_index(drop=True)
        except Exception as e:
            logger.warning(f"{error_msg}:{e}")

    def get_data(
        self, symbol: str, interval: str, start_datetime: pd.Timestamp, end_datetime: pd.Timestamp
    ) -> [pd.DataFrame]:
        def _get_simple(start_, end_):
            self.sleep()
            _remote_interval = interval
            return self.get_data_from_remote(
                symbol,
                interval=_remote_interval,
                start=start_,
                end=end_,
                market_type=self.market_type,
                limit=self.limit,
            )

        return _get_simple(start_datetime, end_datetime)


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


class Run(BaseRun):
    def __init__(self, source_dir=None, normalize_dir=None, max_workers=1, interval="1d", config_path="config/workflow.json"):
        """

        Parameters
        ----------
        source_dir: str
            The directory where the raw data collected from the Internet is saved, default "Path(__file__).parent/source"
        normalize_dir: str
            Directory for normalize data, default "Path(__file__).parent/normalize"
        max_workers: int
            Concurrent number, default is 1
        interval: str
            freq, value from [1min, 5min, 15min, 30min, 1h, 4h, 1d, 1w], default 1d
        """
        self.config_manager = ConfigManager(config_path)
        config = self.config_manager.load_config()

        # Load defaults from config if not provided
        if source_dir is None:
            # Try data.csv_data_dir first, then legacy data_dir, then default
            source_dir = config.get("data", {}).get("csv_data_dir") or config.get("data_dir", "data/klines")

        self.market_type = config.get("data", {}).get("market_type", "spot")
        self.limit = config.get("data_collection", {}).get("limit", 100)

        if interval == "1d": # if default
             # Try to get from config, map 1m to 1min if needed for qlib
             cfg_interval = config.get("data_collection", {}).get("interval", "1d")
             if cfg_interval == '1m':
                 interval = "1min"
             elif cfg_interval == '1d':
                 interval = "1d"
             else:
                 interval = cfg_interval # fallback

        super().__init__(source_dir, normalize_dir, max_workers, interval)

    @property
    def collector_class_name(self):
        return "CryptoCollector"

    @property
    def normalize_class_name(self):
        return "CryptoNormalize"

    @property
    def default_base_dir(self) -> [Path, str]:
        return CUR_DIR

    def download_data(
        self,
        max_collector_count=2,
        delay=0,
        start=None,
        end=None,
        check_data_length: int = None,
        limit_nums=None,
        symbol_file=None,
    ):
        """download data from Internet

        Parameters
        ----------
        max_collector_count: int
            default 2
        delay: float
            time.sleep(delay), default 0
        interval: str
            freq, value from [1min, 1d], default 1d, currently only supprot 1d
        start: str
            start datetime, default "2000-01-01"
        end: str
            end datetime, default ``pd.Timestamp(datetime.datetime.now() + pd.Timedelta(days=1))``
        check_data_length: int # if this param useful?
            check data length, if not None and greater than 0, each symbol will be considered complete if its data length is greater than or equal to this value, otherwise it will be fetched again, the maximum number of fetches being (max_collector_count). By default None.
        limit_nums: int
            using for debug, by default None

        Examples
        ---------
            # get daily data
            $ python collector.py download_data --source_dir ~/.qlib/crypto_data/source/1d --start 2015-01-01 --end 2021-11-30 --delay 1 --interval 1d
        """

        # Load range from configured if not provided
        if start is None:
            start = self.config_manager.get_with_defaults("data_collection", "start_time", "2020-01-01")
        if end is None:
            end = self.config_manager.get("data_collection", "end_time")
            if not end or str(end).strip() == "":
                end = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

        if symbol_file is None:
            symbol_file = self.config_manager.get("data", "symbols")
            if symbol_file:
                 # Resolve relative path
                 full_path = Path(self.config_manager.config_path).parent.parent / symbol_file
                 if full_path.exists():
                     symbol_file = str(full_path)
                 else:
                     logger.warning(f"Symbol file {symbol_file} not found at {full_path}")
            else:
                 logger.info("No symbol file configured, downloading all available symbols.")

        super(Run, self).download_data(
            max_collector_count,
            delay,
            start,
            end,
            check_data_length,
            limit_nums,
            symbol_file=symbol_file,
            market_type=self.market_type,
            limit=self.limit,
        )

    def normalize_data(self, date_field_name: str = "date", symbol_field_name: str = "symbol"):
        """normalize data

        Parameters
        ----------
        date_field_name: str
            date field name, default date
        symbol_field_name: str
            symbol field name, default symbol

        Examples
        ---------
            $ python collector.py normalize_data --source_dir ~/.qlib/crypto_data/source/1d --normalize_dir ~/.qlib/crypto_data/source/1d_nor --interval 1d --date_field_name date
        """
        super(Run, self).normalize_data(date_field_name, symbol_field_name)


if __name__ == "__main__":
    fire.Fire(Run)
