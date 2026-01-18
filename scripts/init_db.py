#!/usr/bin/env python3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
from pathlib import Path

def load_config():
    with open("config/workflow.json", "r") as f:
        return json.load(f)

def init_db():
    config = load_config()
    db_cfg = config.get("database", {})
    
    target_db = db_cfg.get("database", "qlib_crypto")
    user = db_cfg.get("user", "crypto_user")
    password = db_cfg.get("password", "crypto")
    host = db_cfg.get("host", "localhost")
    port = db_cfg.get("port", 5432)
    
    print(f"Checking database: {target_db} on {host}:{port}...")
    
    # Connect to default 'postgres' database to check/create target db
    try:
        conn = psycopg2.connect(
            user=user, 
            password=password, 
            host=host, 
            port=port, 
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if DB exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{target_db}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Database '{target_db}' not found. Creating...")
            cur.execute(f"CREATE DATABASE {target_db}")
            print(f"✅ Database '{target_db}' created successfully.")
        else:
            print(f"✅ Database '{target_db}' already exists.")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print("Hint: Check if PostgreSQL is running and credentials are correct.")
        
if __name__ == "__main__":
    init_db()
