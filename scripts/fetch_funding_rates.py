"""
资金费率数据获取示例

本脚本演示如何从 OKX 获取历史资金费率数据并保存为 CSV 格式。
资金费率是永续合约特有的机制，用于锚定合约价格与现货价格，是重要的市场情绪指标。
"""

import ccxt
import pandas as pd
from datetime import datetime
import time
import os
import sys
import json
from pathlib import Path
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch

CUR_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CUR_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Try importing ConfigManager and symbol utils
try:
    from scripts.config_manager import ConfigManager
    from scripts.symbol_utils import normalize_symbol, get_ccxt_symbol, get_data_path
except ImportError:
    # Fallback if running outside of project structure or if modules missing
    def normalize_symbol(sym: str) -> str:
        s = str(sym).strip().upper()
        if '/' in s: return s
        return s.replace('-', '_').replace(' ', '_')
    
    def get_ccxt_symbol(sym: str) -> str:
        return sym.replace('_', '/')
        
    class ConfigManager:
        def __init__(self, config_path): self.config_path = config_path
        def load_config(self): return {}
        def get(self, s, k, d=None): return d
        def get_with_defaults(self, s, k, d=None): return d

class PostgreSQLStorage:
    def __init__(self, host, port, database, user, password):
        self.conn_params = {
            "host": host, "port": port, "database": database, "user": user, "password": password
        }
        self.conn = None

    def connect(self):
        if not self.conn:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def ensure_table(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS funding_rates (
                    symbol VARCHAR(50),
                    timestamp TIMESTAMP WITH TIME ZONE,
                    funding_rate DOUBLE PRECISION,
                    funding_datetime TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, timestamp)
                );
            """)
            # Ensure index on timestamp for faster merging
            cur.execute("CREATE INDEX IF NOT EXISTS idx_funding_rates_ts ON funding_rates (timestamp);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_funding_rates_sym ON funding_rates (symbol);")

    def save_data(self, data: list):
        if not data: return
        self.connect()
        self.ensure_table()
        
        # Prepare data for insertion
        # data is list of dicts: timestamp (ms), datetime, symbol, funding_rate, funding_datetime
        
        # Convert ms timestamp to datetime if needed, but DB expects timestamp
        # Actually our `all_funding_rates` has 'timestamp' as int ms. DB column is TIMESTAMP WITH TIME ZONE.
        # We should convert in python or let postgres handle to_timestamp(val/1000.0)
        
        rows = []
        for d in data:
            ts = pd.to_datetime(d['timestamp'], unit='ms', utc=True)
            f_dt = d['funding_datetime']
            if f_dt:
                if isinstance(f_dt, (int, float)):
                     f_dt = pd.to_datetime(f_dt, unit='ms', utc=True)
                else:
                     f_dt = pd.to_datetime(f_dt, utc=True)
            
            rows.append((
                d['symbol'],
                ts,
                d['funding_rate'],
                f_dt
            ))

        query = """
            INSERT INTO funding_rates (symbol, timestamp, funding_rate, funding_datetime)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (symbol, timestamp) 
            DO UPDATE SET funding_rate = EXCLUDED.funding_rate, funding_datetime = EXCLUDED.funding_datetime, updated_at = CURRENT_TIMESTAMP;
        """
        
        with self.conn.cursor() as cur:
            execute_batch(cur, query, rows, page_size=1000)
        print(f"Saved {len(rows)} funding rate records to database.")

    def merge_with_ohlcv(self, symbol):
        """
        Merge funding rates into ohlcv_data table for the given symbol.
        Uses a correlated subquery to fill funding_rate from the latest previous funding_rates record.
        """
        self.connect()
        
        # 1. Add column if not exists
        with self.conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE ohlcv_data 
                ADD COLUMN IF NOT EXISTS funding_rate DOUBLE PRECISION;
            """)
        
        print(f"Merging funding rates for {symbol} in DB (This may take a while)...")
        # 2. Update
        # Optimize: only update rows where funding_rate is NULL? Or update all to ensure correctness?
        # User implies "merge", usually meaning fill.
        
        # Note: ohlcv_data has 'symbol', 'timestamp' (timestamptz). funding_rates has 'symbol', 'timestamp'.
        # We match on symbol and find max(fr.timestamp) <= ohlcv.timestamp
        
        query = """
        UPDATE ohlcv_data o
        SET funding_rate = (
            SELECT f.funding_rate
            FROM funding_rates f
            WHERE f.symbol = o.symbol
              AND f.timestamp <= o.timestamp
            ORDER BY f.timestamp DESC
            LIMIT 1
        )
        WHERE o.symbol = %s;
        """
        # Note: this global update can be very slow.
        # A more efficient way might be extracting to temp table, but let's try direct update first.
        # Adding an index on ohlcv_data(symbol, timestamp) helps if not exists.
        
        with self.conn.cursor() as cur:
            cur.execute(query, (symbol,))
            print(f"Updated {cur.rowcount} rows in ohlcv_data for {symbol}.")


def fetch_funding_rate_history(
    symbol: str = "BTC/USDT:USDT",
    exchange_name: str = "binance",
    start_date: str = "2024-01-01",
    end_date: str = "2025-01-01",
    output_dir: str = "data/funding_rates",
    output_format: str = "csv",
    db_config: dict = None
):
    """
    Get historical funding rate data from the specified exchange.
    output_format: "csv" or "db"
    """
    
    # Initialize exchange
    if exchange_name.lower() == 'binance':
        exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    elif exchange_name.lower() == 'okx':
        exchange = ccxt.okx({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}")
    
    # Convert dates to timestamps (ms)
    start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_date).timestamp() * 1000) + 86400000 
    
    all_funding_rates = []
    
    print(f"Fetching funding rates for {symbol} from {exchange_name}...")
    print(f"Time range: {start_date} to {end_date}")
    
    if exchange_name.lower() == 'binance':
        current_ts = start_ts
        while current_ts < end_ts:
            try:
                batch = exchange.fetch_funding_rate_history(symbol, since=current_ts, limit=1000)
                if not batch: break
                    
                batch = [x for x in batch if x['timestamp'] <= end_ts]
                if not batch: break
                    
                for fr in batch:
                    all_funding_rates.append({
                        'timestamp': fr['timestamp'],
                        'datetime': fr['datetime'],
                        'symbol': fr['symbol'],
                        'funding_rate': float(fr['fundingRate']),
                        'funding_datetime': fr.get('fundingTime', None)
                    })
                
                last_ts = batch[-1]['timestamp']
                current_ts = last_ts + 1 if last_ts >= current_ts else current_ts + 1
                
                print(f"Fetched {len(all_funding_rates)} records, latest: {batch[-1]['datetime']}")
                if batch[-1]['timestamp'] >= end_ts: break
                time.sleep(exchange.rateLimit / 1000)
            except Exception as e:
                print(f"Binance Error: {e}")
                break
                
    elif exchange_name.lower() == 'okx':
        print("⚠️ Note: OKX API might only return recent data (approx 3 months).")
        current_ts = start_ts
        first_run = True
        
        while current_ts < end_ts:
            try:
                funding_rates = exchange.fetch_funding_rate_history(symbol, since=current_ts, limit=100)
                if not funding_rates: break
                    
                if first_run and funding_rates[0]['timestamp'] > current_ts + 86400000 * 30:
                     print(f"⚠️ API returned data starting ({funding_rates[0]['datetime']}) much later than requested ({start_date})")
                     first_run = False
                
                new_records = False
                for fr in funding_rates:
                    if all_funding_rates and fr['timestamp'] <= all_funding_rates[-1]['timestamp']: continue
                    if fr['timestamp'] > end_ts: continue
                        
                    all_funding_rates.append({
                        'timestamp': fr['timestamp'],
                        'datetime': fr['datetime'],
                        'symbol': fr['symbol'],
                        'funding_rate': float(fr['fundingRate']),
                        'funding_datetime': fr.get('fundingTime', fr.get('fundingDatetime', None))
                    })
                    new_records = True
                
                if not new_records: break
                current_ts = funding_rates[-1]['timestamp'] + 1
                print(f"Fetched {len(all_funding_rates)} records, latest: {funding_rates[-1]['datetime']}")
                if funding_rates[-1]['timestamp'] >= end_ts: break
                time.sleep(exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"OKX Error: {e}")
                break

    df = pd.DataFrame(all_funding_rates)
    if df.empty:
        print("No funding rate data fetched.")
        return df
    
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    if output_format == "db" and db_config:
        # Save to DB
        storage = PostgreSQLStorage(**db_config)
        # Normalize symbol for storage if needed? 
        # Usually we store raw CCXT symbol or normalized? 
        # okx_data_collector stores "ETHUSDT" (raw) but convert_to_qlib expects that.
        # Here we have "BTC/USDT:USDT".
        # Let's save as-is or normalize. kline data uses "ETHUSDT" (no slash).
        # We should align with kline data symbol format which is typically "ETHUSDT" for Spot, "ETH-USDT-SWAP" for OKX?
        # Wait, okx_data_collector uses `normalize_symbol` which removes slashes "ETH_USDT".
        # Let's strip slashes/colons to match typical qlib raw symbol 'ATP'.
        # Actually okx_data_collector uses `symbol` passed in `update_latest_data`. 
        # It's better to verify what symbol is in `ohlcv_data`.
        # convert_to_qlib says: `Loaded from DB - Symbol: ETH_USDT/240min/FUTURE (Raw: ETHUSDT)`
        # So raw symbol in DB is "ETHUSDT".
        
        # We should convert "BTC/USDT:USDT" -> "BTCUSDT" for DB matching?
        # Or "BTC-USDT-SWAP"?
        # OKX symbol in CCXT is "BTC/USDT:USDT".
        # okx_data_collector `normalize_symbol` -> "BTC_USDT".
        # But `scripts/symbol_utils.py` says `normalize_symbol` returns "BTC_USDT".
        # `convert_to_qlib` logs valid `Raw: ETHUSDT`. 
        # It seems `okx_data_collector` saves `symbol` provided in symbol list locally which is "ETHUSDT" (from user input or config).
        # User config has "BTC_USDT/240min/FUTURE".
        # So we should probably use `normalize_symbol(symbol)` from `symbol_utils` which gives "BTC_USDT".
        # Let's check `scripts/symbol_utils.py` again.
        # `normalize_symbol("BTC/USDT:USDT")` -> "BTC_USDT"?
        # lines 19: replace / with _. -> "BTC_USDT:USDT".
        # It doesn't strip :USDT.
        # "ETHUSDT" -> "ETH_USDT" (line 30).
        
        # We need to make sure the symbol stored in `funding_rates` MATCHES `ohlcv_data`.
        # If `ohlcv_data` has "ETHUSDT" (no underscore), we should use that.
        # BUT `symbol_utils.py` logic `normalize_symbol` tries to add underscore if missing for known quotes.
        # Let's trust `normalize_symbol` for now but remove :USDT if present.
        
        save_sym = symbol.split(':')[0]
        if '/' in save_sym: save_sym = save_sym.replace('/', '')
        if '_' in save_sym: save_sym = save_sym.replace('_', '')
        # "BTCUSDT"
        
        # Re-apply `normalize_symbol` logic might produce "BTC_USDT".
        # Let's check what `okx_data_collector` saves. It saves `symbol` iterating over `symbols`.
        # Config has `symbols` list.
        # If we run with `--all`, we get symbols from config.
        # Currently config has `BTC_USDT/240min/FUTURE`.
        # `process_all_from_config` parses this to `base_sym`="BTC_USDT".
        # Then calls fetch using `ccxt_sym`.
        # We should store using `base_sym` ("BTC_USDT") or simplified "BTCUSDT".
        # Ideally we stick to what `ohlcv_data` has.
        # We previously saw `okx_data_collector` dumping "ETHUSDT" (no underscore) in logs?
        # Stop. check logs Step 200: `Loaded from DB - Symbol: ETH_USDT/240min/FUTURE (Raw: ETHUSDT)`
        # So raw is `ETHUSDT` (no underscore).
        # So we should strip underscores.
        
        db_symbol = symbol.split(':')[0].replace('/', '').replace('_', '')
        
        # Update symbol in all_funding_rates for DB save
        for fr in all_funding_rates:
            fr['symbol'] = db_symbol
            
        storage.save_data(all_funding_rates)
        storage.close()
        print(f"Saved to DB table funding_rates for {db_symbol}")
        return df

    # Save to CSV
    symbol_base = symbol.split(':')[0] if ':' in symbol else symbol
    symbol_clean = normalize_symbol(symbol_base)
    final_output_dir = os.path.join(output_dir, symbol_clean, "funding_rates")
    os.makedirs(final_output_dir, exist_ok=True)
    
    output_file = os.path.join(final_output_dir, f"{symbol_clean}.csv")
    cols = ['timestamp', 'datetime', 'symbol', 'funding_rate', 'funding_datetime']
    for c in cols:
        if c not in df.columns: df[c] = None
            
    df[cols].to_csv(output_file, index=False)
    print(f"\nData saved to: {output_file} ({len(df)} records)")
    return df


def merge_funding_rate_with_ohlcv(ohlcv_file, funding_rate_file, output_file=None):
    """
    Merge funding rate data with OHLCV data.
    """
    if not os.path.exists(ohlcv_file):
        print(f"OHLCV file not found: {ohlcv_file}")
        return None
    if not os.path.exists(funding_rate_file):
        print(f"Funding rate file not found: {funding_rate_file}")
        return None

    ohlcv = pd.read_csv(ohlcv_file, parse_dates=['datetime'] if 'datetime' in pd.read_csv(ohlcv_file, nrows=1).columns else ['date'])
    # Normalize date column name
    if 'date' in ohlcv.columns:
        ohlcv['datetime'] = pd.to_datetime(ohlcv['date'])
        
    if 'funding_rate' in ohlcv.columns:
        ohlcv = ohlcv.drop(columns=['funding_rate'])
    
    funding = pd.read_csv(funding_rate_file, parse_dates=['timestamp'])
    # Avoid duplicate 'datetime' columns if one already exists
    funding = funding[['timestamp', 'funding_rate']].rename(columns={'timestamp': 'datetime'})
    
    # Use merge_asof
    merged = pd.merge_asof(
        ohlcv.sort_values('datetime'),
        funding[['datetime', 'funding_rate']].sort_values('datetime'),
        on='datetime',
        direction='backward'
    )
    
    # Ensure date column is preserved as primary if it existed
    if 'date' in merged.columns and 'datetime' in merged.columns:
         # Check if we need to drop expected duplicate
         pass

    print(f"Merged {len(ohlcv)} OHLCV rows with funding rates. Missing rates: {merged['funding_rate'].isna().sum()}")
    
    if output_file:
        merged.to_csv(output_file, index=False)
        print(f"Merged data saved to: {output_file}")
    
    return merged


def process_all_from_config(config_path):
    """
    Process all symbols defined in the configuration file.
    """
    cm = ConfigManager(config_path)
    config = cm.load_config()
    
    # Extract settings
    csv_data_dir = cm.get("data", "csv_data_dir") or "data/raw/crypto"
    start_time = cm.get_with_defaults("data_collection", "start_time", "2020-01-01")
    end_time = cm.get_with_defaults("data_collection", "end_time") or datetime.now().strftime("%Y-%m-%d")
    
    # We need to respect the interval/market_type structure in csv_data_dir
    # Usually data/raw/crypto/{symbol}/{interval}/{market_type}/{symbol}.csv
    interval = cm.get("data_collection", "interval", "1h")
    market_type = cm.get("data", "market_type", "future")
    
    # DB Config
    db_cfg = config.get("database") or {}
    use_db = db_cfg.get("use_db", False)
    # Map 'qlib_crypto' or whatever strict keys
    db_config_clean = None
    if use_db:
         db_config_clean = {k: v for k,v in db_cfg.items() if k in ['host','port','database','user','password']}

    # Allow simple mappings
    
    # Allow simple mappings
    if interval == "60min": interval = "1h"
    if interval == "1440min": interval = "1d"
    
    symbols = cm.get_crypto_symbols()
    if not symbols:
        print("No symbols found in configuration.")
        return

    print("=" * 60)
    print(f"Bulk Processing Funding Rates")
    print(f"Config: {config_path}")
    print(f"Symbols: {len(symbols)}")
    print(f"Data Dir: {csv_data_dir}")
    print("=" * 60)

    for sym in symbols:
        # sym might be "BTC_USDT/1h/FUTURE" or just "BTC/USDT"
        # Parse qlib symbol to get base components
        if '/' in sym and len(sym.split('/')) == 3:
             parts = sym.split('/')
             base_sym = parts[0] # BTC_USDT
             sym_interval = parts[1]
             sym_market = parts[2].lower()
        else:
             base_sym = normalize_symbol(sym) # BTC_USDT
             sym_interval = interval
             sym_market = market_type.lower()
        
        # CCXT symbol for fetching
        # If internal is BTC_USDT, we want BTC/USDT:USDT for future/swap
        ccxt_sym = get_ccxt_symbol(base_sym)
        # Fix for common issue: get_ccxt_symbol might return BTC/USDT, but for future/swap we often need suffix
        # Assuming linear USDT perp for now based on 'future' market type
        if 'future' in sym_market or 'swap' in sym_market:
            # Check if it already has suffix
            if ':' not in ccxt_sym:
                 ccxt_sym = f"{ccxt_sym}:USDT"

        print(f"\n>> Processing {base_sym} (CCXT: {ccxt_sym})")
        
        # 1. Fetch
        # Output dir for fetch is usually separate or integrated. 
        # Script default is data/funding_rates, but collector might put it in hierarchical
        # Let's stick to the script's default for clean storage: data/funding_rates/{symbol}/funding_rates/
        # Or better, put it where the user expects: {csv_data_dir}
        
        fetch_funding_rate_history(
            symbol=ccxt_sym,
            exchange_name="okx", # Default to OKX per context
            start_date=start_time,
            end_date=end_time,
            output_dir=csv_data_dir,
            output_format="db" if use_db else "csv",
            db_config=db_config_clean
        )
        
        if use_db and db_config_clean:
             # DB Merge
             # We use base_sym e.g. "BTC_USDT" -> "BTCUSDT"
             db_symbol = base_sym.replace('_', '')
             storage = PostgreSQLStorage(**db_config_clean)
             storage.merge_with_ohlcv(db_symbol)
             storage.close()
             continue
        
        # 2. CSV Merge (Legacy)
        
        # 2. Merge
        # Construct path to OHLCV
        # Using get_data_path or manual construction
        # data/raw/crypto/BTC_USDT/1h/future/BTC_USDT.csv
        ohlcv_path = Path(csv_data_dir) / base_sym / sym_interval / sym_market / f"{base_sym}.csv"
        funding_path = Path(csv_data_dir) / base_sym / "funding_rates" / f"{base_sym}.csv"
        
        if ohlcv_path.exists() and funding_path.exists():
            merge_funding_rate_with_ohlcv(
                ohlcv_file=str(ohlcv_path),
                funding_rate_file=str(funding_path),
                output_file=str(ohlcv_path) # Overwrite
            )
        else:
            print(f"Skipping merge: Files missing ({ohlcv_path.exists()}, {funding_path.exists()})")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch and Merge Crypto Funding Rates')
    
    # Mutually exclusive group: either specific symbol or all from config
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-s', '--symbol', type=str, help='Specific symbol (e.g. ETH/USDT:USDT)')
    group.add_argument('--all', action='store_true', help='Process all symbols from config file')
    
    parser.add_argument('-c', '--config', type=str, default='config/workflow.json', help='Path to config file')
    parser.add_argument('-x', '--exchange', type=str, default='binance', choices=['binance', 'okx'])
    parser.add_argument('-b', '--start', type=str, default='2023-01-01')
    parser.add_argument('-e', '--end', type=str, default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('-o', '--output', type=str, default='data/funding_rates')
    parser.add_argument('--format', type=str, default='csv', choices=['csv', 'db'])
    parser.add_argument('--merge', action='store_true')
    parser.add_argument('--ohlcv-file', type=str)
    parser.add_argument('--merge-output', type=str)
    
    args = parser.parse_args()
    
    if args.all or (not args.symbol):
        # Default to all if no specific symbol given, provided config exists
        if os.path.exists(args.config):
            process_all_from_config(args.config)
        else:
            if args.symbol:
                # Fallback to single mode if symbol is provided but config missing (logic handled below)
                pass
            else:
                 print("Please specify --symbol or provide a valid --config file.")
                 sys.exit(1)
    
    if args.symbol:
         # Single symbol mode (legacy support)
        print("=" * 80)
        print("Funding Rate Tool - Single Mode")
        print(f"Exchange: {args.exchange}, Symbol: {args.symbol}")
        print("=" * 80)
        
        df = fetch_funding_rate_history(
            symbol=args.symbol,
            exchange_name=args.exchange,
            start_date=args.start,
            end_date=args.end,
            output_dir=args.output,
            output_format=args.format,
            db_config=ConfigManager(args.config).load_config().get('database') if args.format=='db' else None
        )
        
        if args.format == 'db' and args.merge:
             # Assume db_config is valid if format is db
             cfg = ConfigManager(args.config).load_config().get('database')
             storage = PostgreSQLStorage(
                 host=cfg.get('host'), port=cfg.get('port'), database=cfg.get('database'), user=cfg.get('user'), password=cfg.get('password')
             )
             # db_symbol normalization: strip :USDT, strip _ and /
             db_symbol = args.symbol.split(':')[0].replace('/', '').replace('_', '')
             storage.merge_with_ohlcv(db_symbol)
             storage.close()

        if args.format == 'csv' and args.merge and args.ohlcv_file:
             if df.empty:
                print("No funding data, skipping merge.")
             else:
                symbol_clean = normalize_symbol(args.symbol.split(':')[0])
                funding_file = os.path.join(args.output, symbol_clean, "funding_rates", f"{symbol_clean}.csv")
                merge_funding_rate_with_ohlcv(
                    ohlcv_file=args.ohlcv_file,
                    funding_rate_file=funding_file,
                    output_file=args.merge_output
                )

