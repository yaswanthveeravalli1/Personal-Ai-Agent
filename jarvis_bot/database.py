import sqlite3
import numpy as np
import os

# Use path relative to this script file so it works from any working directory
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            section TEXT NOT NULL,
            entry TEXT NOT NULL,
            embedding BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_entry(user_id, section, entry, embedding):
    conn = sqlite3.connect(DB_FILE)
    existing = conn.execute(
        "SELECT entry FROM memory WHERE user_id=? AND section=?", (user_id, section)
    ).fetchall()
    if any(entry.lower().strip() == e[0].lower().strip() for e in existing):
        conn.close()
        return False  # duplicate
    emb_blob = embedding.astype(np.float32).tobytes()
    conn.execute(
        "INSERT INTO memory (user_id, section, entry, embedding) VALUES (?,?,?,?)",
        (user_id, section, entry, emb_blob)
    )
    conn.commit()
    conn.close()
    return True

def get_all_entries(user_id):
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT section, entry, embedding FROM memory WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return [(s, e, np.frombuffer(b, dtype=np.float32)) for s, e, b in rows]

def delete_entries(user_id, keyword):
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute(
        "SELECT id, entry FROM memory WHERE user_id=?", (user_id,)
    ).fetchall()
    ids = [r[0] for r in rows if keyword.lower() in r[1].lower()]
    for _id in ids:
        conn.execute("DELETE FROM memory WHERE id=?", (_id,))
    conn.commit()
    conn.close()
    return len(ids)
