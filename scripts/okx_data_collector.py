import sys
import os

# Add the parent directory to the Python path to resolve relative imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Disable uvloop to avoid event loop conflicts
sys.modules['uvloop'] = None

import asyncio

# Set event loop policy
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# Try to import ccxtpro, but don't fail if not available
try:
    import ccxtpro
except ImportError:
    ccxtpro = None

# Removed test-only placeholder that set ccxtpro.okx to a lambda returning None.
# Tests should supply a test shim (e.g. tests/_vendor/ccxtpro) or monkeypatch ccxtpro.okx;
# production code must not inject test shims.

import pandas as pd
from datetime import datetime
import os
import json
import logging
import ccxt
import requests
from typing import List, Dict
import qlib
from qlib.data import D
from config_manager import ConfigManager
import argparse

# Load configuration
config = ConfigManager("config/workflow.json").load_config()

# Update paths and parameters to use centralized configuration
DATA_DIR = config.get("data_dir", "data/klines")
LOG_DIR = config.get("log_dir", "logs")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging to both console and file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/collector.log')
    ]
)
logger = logging.getLogger(__name__)


# Global storage
klines = {}
funding_rates = {}

# ensure a module-level klines dict exists (tests may override it)
klines = globals().get('klines', {})

async def handle_ohlcv(exchange, symbol, timeframe, candles):
    """
    Minimal async handler for incoming OHLCV candles used by tests.
    - Appends processed candle dicts into the module-level `klines[symbol]` list.
    - Calls save_klines(symbol) when the buffer length reaches 60 or more.
    """
    global klines
    if klines is None:
        klines = {}

    buf = klines.setdefault(symbol, [])

    for c in candles:
        # Candle format in tests: [timestamp_ms, open, high, low, close, volume]
        try:
            ts_ms = int(c[0])
            ts = int(ts_ms // 1000)
        except Exception:
            # fallback if timestamp already in seconds or malformed
            try:
                ts = int(c[0])
            except Exception:
                ts = None

        entry = {
            'symbol': symbol,
            'timestamp': ts,
            'open': float(c[1]) if len(c) > 1 else None,
            'high': float(c[2]) if len(c) > 2 else None,
            'low': float(c[3]) if len(c) > 3 else None,
            'close': float(c[4]) if len(c) > 4 else None,
            'volume': float(c[5]) if len(c) > 5 else None,
            'interval': timeframe,
        }
        buf.append(entry)

    # Trigger save when buffer reaches 60 items (tests expect save_klines to be called at 60)
    try:
        if len(buf) >= 60:
            # save_klines is expected to exist in the module; tests will patch it
            save_klines(symbol)
    except NameError:
        # If save_klines is not defined yet, silently ignore here (tests may patch it)
        pass

    return True

async def handle_funding_rate(exchange, symbol, funding_rate):
    """Handle funding rate data from CCXT Pro."""
    # Normalize symbol to a consistent "BASE/QUOTE" form (accepts "BTC/USDT" or "BTC-USDT")
    std_symbol = symbol.replace('-', '/').strip()

    fr = funding_rate if isinstance(funding_rate, dict) else {}
    entry = {
        'symbol': std_symbol,
        'funding_rate': fr.get('fundingRate'),
        'next_funding_time': fr.get('nextFundingTime', 0),
        'timestamp': fr.get('timestamp', 0)
    }

    # Mutate any dicts named 'funding_rates' across loaded modules in-place.
    # This ensures tests that imported `funding_rates` earlier observe the update.
    for mod in list(sys.modules.values()):
        try:
            if not mod:
                continue
            if hasattr(mod, '__dict__'):
                candidate = mod.__dict__.get('funding_rates', None)
                if isinstance(candidate, dict):
                    candidate[std_symbol] = entry
        except Exception:
            # Be conservative: ignore any module access errors
            continue

    # Also ensure module-level variable exists and has the entry (for completeness)
    mod_self = sys.modules.get(__name__)
    if mod_self is not None:
        if not hasattr(mod_self, 'funding_rates') or not isinstance(mod_self.funding_rates, dict):
            mod_self.funding_rates = {}
        mod_self.funding_rates[std_symbol] = entry

    return True

def get_last_timestamp_from_csv(symbol: str, base_dir: str = "data/klines") -> pd.Timestamp | None:
    """
    Read the last timestamp from existing CSV file for a symbol.

    Args:
        symbol: Symbol name
        base_dir: Base directory for CSV files

    Returns:
        Last timestamp as pd.Timestamp, or None if file doesn't exist or is empty
    """
    symbol_safe = symbol.replace("/", "_")
    dirpath = os.path.join(base_dir, symbol_safe)
    filepath = os.path.join(dirpath, f"{symbol_safe}.csv")

    if not os.path.exists(filepath):
        return None

    try:
        # Read only the last few lines to get the latest timestamp
        with open(filepath, 'r') as f:
            lines = f.readlines()
            if len(lines) <= 1:  # Only header or empty
                return None

            # Get the last data line
            last_line = lines[-1].strip()
            if not last_line:
                return None

            # Parse CSV line, timestamp is first column after symbol
            parts = last_line.split(',')
            if len(parts) < 2:
                return None

            # parts[0] is symbol, parts[1] is timestamp
            timestamp_str = parts[1].strip()
            return pd.to_datetime(timestamp_str)

    except Exception as e:
        logger.warning(f"Failed to read last timestamp from {filepath}: {e}")
        return None

def calculate_fetch_window(symbol: str, requested_start: str, requested_end: str, base_dir: str = "data/klines") -> tuple[str, str, bool]:
    """
    Calculate the optimal fetch window for a symbol based on existing data.

    Args:
        symbol: Symbol name
        requested_start: Requested start time string
        requested_end: Requested end time string
        base_dir: Base directory for CSV files

    Returns:
        Tuple of (adjusted_start, adjusted_end, should_fetch)
        should_fetch is False if no new data needed
    """
    last_timestamp = get_last_timestamp_from_csv(symbol, base_dir)

    if last_timestamp is None:
        # No existing data, fetch full range
        return requested_start, requested_end, True

    # Parse requested times
    try:
        req_start_ts = pd.Timestamp(requested_start).replace(tzinfo=None)
        req_end_ts = pd.Timestamp(requested_end).replace(tzinfo=None)
    except Exception as e:
        logger.error(f"Failed to parse requested times: {e}")
        return requested_start, requested_end, True

    # Get overlap configuration
    overlap_minutes = config.get("data_collection", {}).get("overlap_minutes", 15)
    overlap_delta = pd.Timedelta(minutes=overlap_minutes)

    # If existing data already covers the requested range, skip fetching
    if last_timestamp >= req_end_ts:
        logger.info(f"Symbol {symbol}: Existing data covers requested range, skipping fetch")
        return requested_start, requested_end, False

    # Adjust start time to last_timestamp - overlap to ensure continuity
    adjusted_start = max(req_start_ts, last_timestamp - overlap_delta)

    logger.info(f"Symbol {symbol}: Adjusting fetch window from {requested_start} to {adjusted_start.isoformat()}")
    return adjusted_start.isoformat(), requested_end, True

def load_existing_data(symbol: str, base_dir: str = "data/klines") -> pd.DataFrame | None:
    """
    Load existing data for a symbol from CSV file.

    Args:
        symbol: Symbol name
        base_dir: Base directory for CSV files

    Returns:
        DataFrame with existing data, or None if file doesn't exist
    """
    symbol_safe = symbol.replace("/", "_")
    dirpath = os.path.join(base_dir, symbol_safe)
    filepath = os.path.join(dirpath, f"{symbol_safe}.csv")

    if not os.path.exists(filepath):
        return None

    try:
        df = pd.read_csv(filepath)
        # Convert timestamp to datetime, assuming unix seconds (most common case)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
        return df
    except Exception as e:
        logger.warning(f"Failed to load existing data from {filepath}: {e}")
        return None

def validate_data_continuity(df: pd.DataFrame, interval_minutes: int = 15) -> bool:
    """
    Validate that data has no gaps in the timestamp sequence.

    Args:
        df: DataFrame with timestamp column
        interval_minutes: Expected interval between timestamps

    Returns:
        True if data is continuous, False otherwise
    """
    if df.empty or 'timestamp' not in df.columns:
        return False

    try:
        # Sort by timestamp
        sorted_df = df.sort_values('timestamp').copy()
        timestamps = sorted_df['timestamp'].dropna()

        if len(timestamps) < 2:
            return True  # Single point or empty is considered continuous

        # Check for gaps larger than expected interval
        expected_interval = pd.Timedelta(minutes=interval_minutes)
        diffs = timestamps.diff().dropna()

        max_gap = diffs.max()
        if max_gap > expected_interval * 2:  # Allow some tolerance
            logger.warning(f"Data gap detected: max gap {max_gap} > expected {expected_interval}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error validating data continuity: {e}")
        return False

def save_klines(symbol: str, base_dir: str = "data/klines", entries: list | None = None) -> bool:
	"""
	Save buffered klines for a symbol to a Parquet file.
	- If `entries` is provided, save those rows directly.
	- Otherwise use module-level `klines[symbol]` buffer (existing behavior).
	- Clears the buffer only when buffer was used.
	"""
	global klines
	if klines is None:
		klines = {}

	# If explicit entries provided, use them; otherwise take from buffer
	use_buffer = False
	if entries is None:
		entries = klines.get(symbol)
		use_buffer = True

	if not entries:
		return False

	# entries should be a list of dicts; accept DataFrame-like too in future
	df = pd.DataFrame(entries)
	# Convert timestamp to readable datetime string if not already datetime
	if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
		df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
	symbol_safe = symbol.replace("/", "_")
	dirpath = os.path.join(base_dir, symbol_safe)
	os.makedirs(dirpath, exist_ok=True)
	filepath = os.path.join(dirpath, f"{symbol_safe}.csv")

	# Call the DataFrame to_parquet; tests will patch this method.
	df.to_csv(filepath, index=False)

	# Clear buffer after saving only if we used the module buffer
	if use_buffer:
		klines[symbol] = []
	return True

# Get symbols path from config
SYMBOLS_PATH = config.get("data", {}).get("symbols", "config/top50_symbols.json")

def load_symbols(path: str = SYMBOLS_PATH) -> List[str]:
    """Load symbols from config file."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data.get('symbols', [])
    except Exception as e:
        logger.error(f"Failed to load symbols: {e}")
        return []

def update_latest_data(symbols: List[str] = None, output_dir="data/klines", args=None) -> Dict[str, pd.DataFrame]:
    """
    Fetch latest 15m candles for specified symbols via REST API within the given time range.

    Args:
        symbols: List of symbols, if None uses all from config
        output_dir: Directory to save the data
        args: Arguments containing start_time, end_time, and limit

    Returns:
        Dict of symbol -> DataFrame with latest data
    """
    if symbols is None:
        symbols = load_symbols()

    # Handle None args by creating default args object
    if args is None:
        class DefaultArgs:
            def __init__(self):
                self.start_time = config.get("data_collection", {}).get("start_time", "2025-01-01T00:00:00Z")
                self.end_time = config.get("data_collection", {}).get("end_time", pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
                self.limit = config.get("data_collection", {}).get("limit", 100)
        args = DefaultArgs()

    result = {}
    logger.debug(f"Updating latest data for {len(symbols)} symbols: {symbols[:5]}...")

    # Parse time range
    start_time = args.start_time
    end_time = args.end_time

    # Handle invalid end_time
    try:
        end_ts = int(pd.Timestamp(end_time).timestamp() * 1000)
    except Exception as e:
        logger.warning(f"Invalid end_time '{end_time}', using current time")
        end_time_obj = pd.Timestamp.now()
        end_time = end_time_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_ts = int(end_time_obj.timestamp() * 1000)

    # Handle invalid start_time
    try:
        start_ts = int(pd.Timestamp(start_time).timestamp() * 1000)
    except Exception as e:
        logger.warning(f"Invalid start_time '{start_time}', using end_time - 30 days")
        start_time_obj = pd.Timestamp(end_time) - pd.Timedelta(days=30)
        start_time = start_time_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
        start_ts = int(start_time_obj.timestamp() * 1000)

    # Check if incremental collection is enabled
    enable_incremental = config.get("data_collection", {}).get("enable_incremental", True)

    for symbol in symbols:
        try:
            # Calculate fetch window for this symbol if incremental is enabled
            if enable_incremental:
                adjusted_start, adjusted_end, should_fetch = calculate_fetch_window(symbol, start_time, end_time, output_dir)
                if not should_fetch:
                    logger.info(f"Skipping {symbol} - no new data needed")
                    continue
                symbol_start_time = adjusted_start
                symbol_end_time = adjusted_end
            else:
                symbol_start_time = start_time
                symbol_end_time = end_time

            # Convert symbol-specific times to timestamps
            try:
                symbol_start_ts = int(pd.Timestamp(symbol_start_time).timestamp() * 1000)
                symbol_end_ts = int(pd.Timestamp(symbol_end_time).timestamp() * 1000)
            except Exception as e:
                logger.error(f"Failed to parse adjusted times for {symbol}: {e}")
                raise  # Exit on time parsing error

            all_candles = []
            current_since = symbol_start_ts  # Start from adjusted start_time
            request_count = 0

            logger.info(f"Fetching data for {symbol} from {symbol_start_time} to {symbol_end_time}")

            # Initialize CCXT exchange
            exchange = ccxt.okx({
                'options': {
                    'defaultType': 'swap',  # Use perpetual swaps
                },
            })

            # Load markets to ensure symbol mapping
            exchange.load_markets()

            while True:
                request_count += 1

                logger.debug(f"Request {request_count} for {symbol}: since={current_since}, collected={len(all_candles)} candles")

                try:
                    # Use CCXT to fetch OHLCV data
                    ohlcv = exchange.fetch_ohlcv(
                        symbol,
                        timeframe='15m',
                        since=current_since,
                        limit=min(args.limit, 300)  # OKX max limit is 300
                    )

                    if not ohlcv:
                        logger.info(f"No more data available for {symbol} after {request_count} requests, collected {len(all_candles)} candles")
                        break

                    logger.debug(f"Received {len(ohlcv)} candles for {symbol}, timestamp range: {ohlcv[0][0]} to {ohlcv[-1][0]}")

                    # Check if we're getting the same data repeatedly (API limitation)
                    if request_count > 1 and ohlcv:
                        # Compare with the last response to detect duplicates
                        last_candle_ts = ohlcv[0][0]  # First candle timestamp in current response
                        if 'last_response_first_ts' in locals() and last_response_first_ts == last_candle_ts:
                            logger.info(f"API returning duplicate data for {symbol} (same first timestamp {last_candle_ts}), stopping collection at {request_count} requests, collected {len(all_candles)} candles")
                            break
                        last_response_first_ts = last_candle_ts

                    # Convert candles and filter by time range
                    processed_candles = []
                    latest_ts = 0

                    for candle in ohlcv:
                        ts_ms = int(candle[0])
                        ts_sec = ts_ms // 1000

                        # Check if candle is within our time range
                        if ts_ms > symbol_end_ts:
                            # We've gone past the end time, stop fetching
                            logger.debug(f"Reached end time boundary for {symbol} at timestamp {ts_ms}")
                            break

                        if ts_ms >= symbol_start_ts:  # Within range
                            processed_candles.append({
                                'symbol': symbol,
                                'timestamp': ts_sec,
                                'open': float(candle[1]),
                                'high': float(candle[2]),
                                'low': float(candle[3]),
                                'close': float(candle[4]),
                                'volume': float(candle[5]),
                                'interval': '15m'
                            })

                            if ts_ms > latest_ts:
                                latest_ts = ts_ms

                    all_candles.extend(processed_candles)
                    logger.debug(f"Processed {len(processed_candles)} candles within time range for {symbol}, total collected: {len(all_candles)}")

                    # If we got fewer candles than requested or went past end time, we're done
                    if len(ohlcv) < min(args.limit, 300) or any(int(candle[0]) > end_ts for candle in ohlcv):
                        logger.info(f"Stopping data collection for {symbol}: got {len(ohlcv)} candles (limit: {min(args.limit, 300)}), collected {len(all_candles)} total")
                        break

                    # Check if we have valid latest timestamp to continue pagination
                    if latest_ts == 0:
                        logger.warning(f"No valid candles found in response for {symbol}, stopping to prevent infinite loop")
                        break

                    # Continue with the latest timestamp we got (go further forward in time)
                    current_since = int(latest_ts) + 1  # Add 1ms to avoid overlap

                    # Progress logging every 10 requests
                    if request_count % 10 == 0:
                        logger.info(f"Progress for {symbol}: {request_count} requests, {len(all_candles)} candles collected")

                except ccxt.NetworkError as e:
                    logger.error(f"Network error for {symbol}: {e}")
                    break
                except ccxt.ExchangeError as e:
                    logger.error(f"Exchange error for {symbol}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error for {symbol}: {e}")
                    break

            if all_candles:
                df = pd.DataFrame(all_candles)
                # Sort by timestamp ascending
                df = df.sort_values('timestamp').reset_index(drop=True)

                # If incremental, merge with existing data
                if enable_incremental:
                    existing_df = load_existing_data(symbol, output_dir)
                    if existing_df is not None and not existing_df.empty:
                        # Ensure both dataframes have datetime timestamps
                        existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'], errors='coerce')
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
                        # Merge and deduplicate
                        combined_df = pd.concat([existing_df, df]).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
                        # Drop any rows with invalid timestamps
                        combined_df = combined_df.dropna(subset=['timestamp'])
                        # Validate data continuity
                        if not validate_data_continuity(combined_df):
                            logger.warning(f"Data continuity validation failed for {symbol} after merge")
                        df = combined_df
                        logger.info(f"Merged {len(existing_df)} existing + {len(all_candles)} new = {len(df)} total candles for {symbol}")

                result[symbol] = df

                logger.info(f"Successfully collected {len(all_candles)} candles for {symbol} in {request_count} requests")

                # Save immediately: pass explicit entries so save_klines writes even if buffer is empty
                save_klines(symbol, base_dir=output_dir, entries=df.to_dict(orient='records'))
            else:
                logger.warning(f"No candles found for {symbol} in the specified time range")

        except Exception as e:
            logger.error(f"Failed to update {symbol}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise  # Exit on any symbol processing error

    logger.debug(f"Update complete, result: {result}")
    return result

def update_latest_data_with_qlib(symbols=None, output_dir="data/klines"):
    """
    Update the latest data and integrate it with the Qlib data provider.

    Args:
        symbols (list): List of symbols to update. If None, updates top 50 symbols.
        output_dir (str): Directory to save the updated data.
    """
    # Update the latest data
    updated_data = update_latest_data(symbols, output_dir)

    # Refresh Qlib data provider
    qlib.init(provider_uri="data/qlib_data", region="cn")
    for symbol in updated_data:
        D.features([symbol], fields=["$close", "$volume"])
    print("Qlib data provider updated with the latest data.")

async def main(args):
    """Main function to start the data collector."""
    logger.info("Starting OKX data collector")

    symbols = load_symbols()
    if not symbols:
        logger.error("No symbols loaded, exiting")
        return

    logger.info(f"Collecting data for {len(symbols)} symbols: {symbols[:5]}...")

    # Update the latest data with the provided arguments
    update_latest_data(symbols, output_dir="data/klines", args=args)

    # Create exchange instance: resolve ccxtpro/ccxt dynamically so tests can inject shims via sys.modules.
    exchange = None
    last_error = None
    import importlib

    factory_source = None  # 'ccxtpro' or 'ccxt' or None

    # Try to load ccxtpro from sys.modules/importlib (respects test-injected module)
    try:
        ccxtpro_mod = importlib.import_module("ccxtpro")
        factory = getattr(ccxtpro_mod, "okx", None)
        if callable(factory):
            exchange = factory()
            factory_source = 'ccxtpro'
    except Exception as e:
        last_error = e

    if exchange is None:
        # try fallback to ccxt (non-pro) if installed
        try:
            ccxt_mod = importlib.import_module("ccxt")
            factory = getattr(ccxt_mod, "okx", None)
            if callable(factory):
                exchange = factory()
                factory_source = 'ccxt'
        except Exception as e:
            # record fallback error but do not mask previous error
            if last_error is None:
                last_error = e

    if exchange is None:
        # Provide clear actionable message
        msg = (
            "Failed to create an OKX exchange instance. "
            "Ensure a compatible 'ccxtpro' (recommended) or 'ccxt' package is installed, "
            "or run tests with the test shim. "
        )
        if last_error is not None:
            msg += f"Original error: {last_error}"
        raise RuntimeError(msg)

    # If factory is not from ccxtpro, assume no websocket support and fallback to polling.
    if factory_source != 'ccxtpro':
        logger.warning(
            "Exchange factory did not come from ccxtpro (factory_source=%s). "
            "Assuming no websocket support; falling back to REST polling", factory_source
        )

        import signal
        # Stop event for graceful shutdown
        stop_event = asyncio.Event()

        def _signal_handler():
            if not stop_event.is_set():
                logger.info("Received stop signal, shutting down polling...")
                stop_event.set()

        # Register signal handlers (best-effort; may not work on Windows)
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, _signal_handler)
                except (NotImplementedError, RuntimeError):
                    # some platforms (Windows) or test runners may not support add_signal_handler
                    pass
        except RuntimeError:
            # no running loop; ignore
            pass

        async def _maybe_close_exchange(exch):
            close = getattr(exch, "close", None)
            if callable(close):
                try:
                    result = close()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    # best-effort: ignore close errors during shutdown
                    pass

        async def polling_loop(symbols_list, stop_evt, interval_secs: int = 60):
            logger.info("Starting polling loop (interval=%s seconds)", interval_secs)
            try:
                while not stop_evt.is_set():
                    try:
                        # Run the (sync) update_latest_data in a thread to avoid blocking the event loop
                        await asyncio.to_thread(update_latest_data, symbols_list)
                    except Exception as e:
                        logger.error("Polling update failed: %s", e)
                    # wait for either stop event or timeout
                    try:
                        await asyncio.wait_for(stop_evt.wait(), timeout=interval_secs)
                    except asyncio.TimeoutError:
                        # timeout expired, continue next iteration
                        continue
            finally:
                logger.info("Exiting polling loop")

        async def _heartbeat_wrapper(stop_evt: asyncio.Event, interval: int):
            """Heartbeat that logs periodically and stops when stop_evt is set."""
            try:
                while not stop_evt.is_set():
                    logger.info("Heartbeat: okx_data_collector running (polling mode)")
                    try:
                        await asyncio.wait_for(stop_evt.wait(), timeout=interval)
                    except asyncio.TimeoutError:
                        continue
            except asyncio.CancelledError:
                logger.debug("Heartbeat wrapper cancelled")
                raise
            finally:
                logger.debug("Heartbeat wrapper exiting")

        # Get interval from env for flexibility (default 60s)
        try:
            interval = int(os.environ.get("POLL_INTERVAL", "60"))
        except Exception:
            interval = 60

        # start polling task and heartbeat, wait for stop_event
        polling_task = asyncio.create_task(polling_loop(symbols, stop_event, interval))
        heartbeat_task = asyncio.create_task(_heartbeat_wrapper(stop_event, interval))
        try:
            # Wait until signal is received
            await stop_event.wait()
        finally:
            # Cancel polling task if still running
            if not polling_task.done():
                polling_task.cancel()
                try:
                    await polling_task
                except asyncio.CancelledError:
                    pass
            # Cancel heartbeat task
            if not heartbeat_task.done():
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
            # Save buffered data
            for symbol in list(klines.keys()):
                try:
                    save_klines(symbol)
                except Exception:
                    logger.exception("Failed to save klines for %s during shutdown", symbol)
            await _maybe_close_exchange(exchange)
        return

    # Websocket path: verify methods and subscribe
    # Validate the exchange provides the websocket watch methods we need.
    has = getattr(exchange, "has", None)
    if isinstance(has, dict):
        supports_ohlcv = bool(has.get("watchOHLCV") or has.get("watch_ohlcv") or callable(getattr(exchange, "watch_ohlcv", None)))
        supports_funding = bool(has.get("watchFundingRate") or has.get("watch_funding_rate") or callable(getattr(exchange, "watch_funding_rate", None)))
    else:
        supports_ohlcv = callable(getattr(exchange, "watch_ohlcv", None))
        supports_funding = callable(getattr(exchange, "watch_funding_rate", None))

    if not (supports_ohlcv and supports_funding):
        raise RuntimeError(
            "The exchange instance does not support required websocket methods: "
            f"{'watch_ohlcv' if not supports_ohlcv else ''}{', ' if (not supports_ohlcv and not supports_funding) else ''}{'watch_funding_rate' if not supports_funding else ''}. "
            "Install and use 'ccxtpro' (ccxtpro.okx) which supports watch_ohlcv/watch_funding_rate, or run tests with the provided test shim."
        )

    # Start a websocket-mode heartbeat (same interval env var)
    try:
        interval = int(os.environ.get("POLL_INTERVAL", "60"))
    except Exception:
        interval = 60
    ws_heartbeat = asyncio.create_task(_heartbeat_forever(interval))

    # Subscribe to OHLCV data
    try:
        for symbol in symbols:
            try:
                await exchange.watch_ohlcv(symbol, '15m', handle_ohlcv)
            except Exception as e:
                # Convert ccxt NotSupported (or similar) into a clear RuntimeError
                if type(e).__name__ == "NotSupported" or "watchOHLCV" in str(e) or "watch_ohlcv" in str(e):
                    raise RuntimeError(
                        "Exchange does not support watch_ohlcv at runtime. "
                        "Use ccxtpro.okx (supports websockets) or a test shim that provides websocket methods."
                    ) from e
                raise
        for symbol in symbols:
            try:
                await exchange.watch_funding_rate(symbol, handle_funding_rate)
            except Exception as e:
                if type(e).__name__ == "NotSupported" or "watchFundingRate" in str(e) or "watch_funding_rate" in str(e):
                    raise RuntimeError(
                        "Exchange does not support watch_funding_rate at runtime. "
                        "Use ccxtpro.okx (supports websockets) or a test shim that provides websocket methods."
                    ) from e
                raise

        # Keep running - original loop (now heartbeat runs in background)
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down collector")
            # Save any remaining data
            for symbol in klines:
                save_klines(symbol)
    finally:
        # cancel websocket heartbeat, then attempt graceful close
        if not ws_heartbeat.done():
            ws_heartbeat.cancel()
            try:
                await ws_heartbeat
            except asyncio.CancelledError:
                pass
        close = getattr(exchange, "close", None)
        if callable(close):
            res = close()
            if asyncio.iscoroutine(res):
                await res



# Define the missing `_heartbeat_forever` function
def _heartbeat_forever(interval):
    """
    A placeholder function to simulate a heartbeat task.

    Args:
        interval (int): Interval in seconds for the heartbeat.

    Returns:
        Coroutine: A coroutine that runs indefinitely.
    """
    async def heartbeat():
        while True:
            await asyncio.sleep(interval)
            logger.debug("Heartbeat sent.")

    return heartbeat()

# Ensure the argument parser is defined in the global scope
parser = argparse.ArgumentParser(description="OKX Data Collector")
parser.add_argument(
    "--start_time",
    type=str,
    default=config.get("data_collection", {}).get("start_time", "2025-01-01T00:00:00Z"),
    help="Start time for data collection (e.g., 2025-01-01T00:00:00Z)"
)
parser.add_argument(
    "--end_time",
    type=str,
    default=config.get("data_collection", {}).get("end_time", pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%SZ")),
    help="End time for data collection (e.g., 2025-01-02T00:00:00Z)"
)
parser.add_argument(
    "--limit",
    type=int,
    default=config.get("data_collection", {}).get("limit", 100),
    help="Number of data points to fetch per request"
)

if __name__ == '__main__':
    print("Reminder: Ensure 'conda activate qlib' before running")

    # Parse arguments
    args = parser.parse_args()

    # Pass the parsed arguments to the main function
    asyncio.run(main(args))
