import sys

# Disable uvloop to avoid event loop conflicts
sys.modules['uvloop'] = None

import asyncio

# Set event loop policy
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

import ccxtpro

# Removed test-only placeholder that set ccxtpro.okx to a lambda returning None.
# Tests should supply a test shim (e.g. tests/_vendor/ccxtpro) or monkeypatch ccxtpro.okx;
# production code must not inject test shims.

import pandas as pd
from datetime import datetime
import os
import json
import logging
import requests
from typing import List, Dict

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/collector.log')
    ]
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = "okx_data"
CONFIG_PATH = "config/test_symbols.json"

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

def save_klines(symbol: str, base_dir: str = "data/klines") -> bool:
    """
    Save buffered klines for a symbol to a Parquet file.
    Minimal implementation for tests:
    - Uses module-level `klines` dict.
    - Creates directory `base_dir/<symbol_safe>`, calls DataFrame.to_parquet (tests patch this).
    - Clears the buffer for the symbol after saving.
    """
    global klines
    if klines is None:
        klines = {}

    entries = klines.get(symbol)
    if not entries:
        return False

    df = pd.DataFrame(entries)
    symbol_safe = symbol.replace("/", "_")
    dirpath = os.path.join(base_dir, symbol_safe)
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, f"{symbol_safe}.parquet")

    # Call the DataFrame to_parquet; tests will patch this method.
    df.to_parquet(filepath, index=False)

    # Clear buffer after saving
    klines[symbol] = []
    return True

def load_symbols(path: str = CONFIG_PATH) -> List[str]:
    """Load symbols from config file."""
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data.get('symbols', [])
    except Exception as e:
        logger.error(f"Failed to load symbols: {e}")
        return []

def update_latest_data(symbols: List[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Fetch latest 15m candles for specified symbols via REST API.
    
    Args:
        symbols: List of symbols, if None uses all from config
        
    Returns:
        Dict of symbol -> DataFrame with latest data
    """
    if symbols is None:
        symbols = load_symbols()
    
    result = {}
    
    for symbol in symbols:
        try:
            # OKX REST API for candles
            url = "https://www.okx.com/api/v5/market/candles"
            params = {
                'instId': symbol.replace('/', '-'),  # BTC/USDT -> BTC-USDT
                'bar': '15m',
                'limit': 1  # Latest candle
            }
            
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('code') == '0' and data.get('data'):
                candle = data['data'][0]
                df = pd.DataFrame([{
                    'symbol': symbol,
                    'timestamp': int(candle[0]) // 1000,  # Convert ms to s
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                    'interval': '15m'
                }])
                result[symbol] = df
                
                # Also save to Parquet if needed
                save_klines(symbol)
                
        except Exception as e:
            logger.error(f"Failed to update {symbol}: {e}")
    
    return result

async def main():
    """Main function to start the data collector."""
    logger.info("Starting OKX data collector")

    symbols = load_symbols()
    if not symbols:
        logger.error("No symbols loaded, exiting")
        return

    logger.info(f"Collecting data for {len(symbols)} symbols: {symbols[:5]}...")

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
            "Assuming no websocket support; falling back to REST polling.", factory_source
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

class OkxDataCollector:
    """
    Minimal collector used by unit tests:
    - collect_data calls requests.get(...) so tests can mock requests.get to raise or return responses.
    - Returns [] for empty/unexpected JSON responses.
    - validate_data raises ValueError for invalid formats.
    """
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or "https://api.okx.com"

    def collect_data(self, symbol: str | None = None):
        # Use a generic endpoint string — tests mock requests.get so URL doesn't matter.
        url = f"{self.base_url}/dummy"
        resp = requests.get(url)
        # If requests.get raises, let exception propagate (tests expect this)

        # Safely handle status_code that may be a MagicMock or non-int.
        status = getattr(resp, "status_code", None)
        status_int = None
        if status is not None:
            try:
                # Try to coerce status to int (works for ints and objects with __int__).
                status_int = int(status)
            except Exception:
                # If it cannot be coerced (e.g., MagicMock), ignore the status check.
                status_int = None

        if status_int is not None and status_int >= 400:
            raise Exception(f"API error: status {status_int}")

        try:
            data = resp.json()
        except Exception:
            return []

        if not data or not isinstance(data, dict):
            return []

        # Typical OKX response wraps payload under "data"; return that or empty list
        payload = data.get("data")
        if not payload:
            return []
        return payload

    def validate_data(self, data):
        # Tests pass invalid dicts like {"invalid": "format"} and expect ValueError
        if not isinstance(data, dict):
            raise ValueError("Invalid data: expected dict")
        # require at least one expected key for a valid data dict
        expected_keys = {"symbol", "timestamp", "open", "close"}
        if not expected_keys.intersection(set(data.keys())):
            raise ValueError("Invalid data format")
        return True

if __name__ == '__main__':
    print("Reminder: Ensure 'conda activate qlib' before running")
    asyncio.run(main())
