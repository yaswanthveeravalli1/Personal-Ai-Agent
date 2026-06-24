import sqlite3
import psycopg2
import os
import sys

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

SQLITE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")

def get_pg_conn():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or "YOUR_SUPABASE" in db_url or "[password]" in db_url:
        print("ERROR: Invalid or missing DATABASE_URL. Please update it in .env first.")
        sys.exit(1)
    return psycopg2.connect(db_url)

def migrate():
    if not os.path.exists(SQLITE_DB):
        print(f"Local database not found at {SQLITE_DB}")
        sys.exit(1)
    
    print("Connecting to local SQLite database...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cur = sqlite_conn.cursor()
    
    try:
        sqlite_cur.execute("SELECT user_id, section, entry, embedding, created_at FROM memory")
        rows = sqlite_cur.fetchall()
    except Exception as e:
        print(f"Failed to read local DB: {e}")
        sys.exit(1)
    
    if not rows:
        print("No records found in local memory.db.")
        sqlite_conn.close()
        sys.exit(0)
    
    print(f"Found {len(rows)} records in local DB.")
    
    print("Connecting to Supabase PostgreSQL...")
    try:
        pg_conn = get_pg_conn()
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        sys.exit(1)
        
    pg_cur = pg_conn.cursor()
    
    # Ensure table exists in Supabase
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            section TEXT NOT NULL,
            entry TEXT NOT NULL,
            embedding BYTEA NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    pg_conn.commit()
    
    print("Migrating records to Supabase...")
    migrated = 0
    for user_id, section, entry, embedding, created_at in rows:
        pg_cur.execute(
            "INSERT INTO memory (user_id, section, entry, embedding, created_at) VALUES (%s, %s, %s, %s, %s)",
            (user_id, section, entry, psycopg2.Binary(embedding), created_at)
        )
        migrated += 1
        if migrated % 100 == 0:
            print(f"  {migrated} / {len(rows)} records copied...")
            pg_conn.commit()
            
    pg_conn.commit()
    print(f"Successfully migrated {migrated} records to Supabase!")
    
    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()
    
    print("\nMigration complete! You can now safely exclude the local memory.db file.")

if __name__ == "__main__":
    migrate()
