import psycopg2
import numpy as np
import os
import config  # This ensures load_dotenv() is called

def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing. Please set it in .env or Render dashboard.")
    return psycopg2.connect(db_url)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            section TEXT NOT NULL,
            entry TEXT NOT NULL,
            embedding BYTEA NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_entry(user_id, section, entry, embedding):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT entry FROM memory WHERE user_id=%s AND section=%s", (user_id, section)
    )
    existing = cur.fetchall()
    if any(entry.lower().strip() == e[0].lower().strip() for e in existing):
        cur.close()
        conn.close()
        return False  # duplicate
    emb_blob = embedding.astype(np.float32).tobytes()
    cur.execute(
        "INSERT INTO memory (user_id, section, entry, embedding) VALUES (%s,%s,%s,%s)",
        (user_id, section, entry, psycopg2.Binary(emb_blob))
    )
    conn.commit()
    cur.close()
    conn.close()
    return True

def get_all_entries(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT section, entry, embedding FROM memory WHERE user_id=%s", (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [(s, e, np.frombuffer(b, dtype=np.float32)) for s, e, b in rows]

def delete_entries(user_id, keyword):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, entry FROM memory WHERE user_id=%s", (user_id,)
    )
    rows = cur.fetchall()
    ids = [r[0] for r in rows if keyword.lower() in r[1].lower()]
    for _id in ids:
        cur.execute("DELETE FROM memory WHERE id=%s", (_id,))
    conn.commit()
    cur.close()
    conn.close()
    return len(ids)
