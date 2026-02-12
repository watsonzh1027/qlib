
import sys
import os
import psycopg2
from psycopg2 import sql
import json

def load_db_config():
    with open('config/workflow.json', 'r') as f:
        config = json.load(f)
    return config.get('database', {})

def check_and_fix_schema():
    db_config = load_db_config()
    
    conn = psycopg2.connect(
        host=db_config.get("host", "localhost"),
        database=db_config.get("database", "qlib_crypto"),
        user=db_config.get("user", "crypto_user"),
        password=db_config.get("password", "change_me_in_production"),
        port=db_config.get("port", 5432)
    )
    conn.autocommit = True
    
    table_name = "ohlcv_data"
    
    try:
        with conn.cursor() as cursor:
            # Check existing columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
            """, (table_name,))
            
            existing_columns = {row[0] for row in cursor.fetchall()}
            print(f"Existing columns in {table_name}: {existing_columns}")
            
            columns_to_add = {
                'vwap': 'DOUBLE PRECISION',
                'funding_rate': 'DOUBLE PRECISION'
            }
            
            for col, dtype in columns_to_add.items():
                if col not in existing_columns:
                    print(f"Adding missing column: {col}")
                    cursor.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                        sql.Identifier(table_name),
                        sql.Identifier(col),
                        sql.SQL(dtype)
                    ))
                    print(f"Added column {col}.")
                else:
                    print(f"Column {col} already exists.")
                    
    except Exception as e:
        print(f"Error checking/fixing schema: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_and_fix_schema()
