"""
Migration script: Re-embed all existing memories in memory.db using the new
128-dim hash-trick vectorizer. This fixes the dimension mismatch caused by
switching from sentence-transformers (384-dim) to the hash vectorizer (128-dim).

Run this from the jarvis_bot directory:
    python migrate_embeddings.py
"""
import sqlite3
import numpy as np
import hashlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_FILE = os.path.join(os.path.dirname(__file__), "memory.db")

def stable_hash(word):
    return int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)

def embed(text):
    vector = np.zeros(128, dtype=np.float32)
    words = text.lower().split()
    for w in words:
        idx = stable_hash(w) % 128
        vector[idx] += 1.0
    return vector

def migrate():
    print(f"[Migrate] Opening database: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)

    rows = conn.execute("SELECT id, entry, embedding FROM memory").fetchall()
    if not rows:
        print("[Migrate] No entries found in database. Nothing to migrate.")
        conn.close()
        return

    print(f"[Migrate] Found {len(rows)} entries. Re-embedding with 128-dim hash vectorizer...")

    migrated = 0
    skipped = 0
    for row_id, entry, emb_blob in rows:
        # Check current dimension
        try:
            current_emb = np.frombuffer(emb_blob, dtype=np.float32)
            if len(current_emb) == 128:
                skipped += 1
                continue  # already 128-dim, skip
        except Exception:
            pass

        # Re-embed with new vectorizer
        new_emb = embed(entry)
        new_blob = new_emb.tobytes()
        conn.execute("UPDATE memory SET embedding=? WHERE id=?", (new_blob, row_id))
        migrated += 1

    conn.commit()
    conn.close()

    print(f"[Migrate] Done!")
    print(f"   Re-embedded : {migrated} entries")
    print(f"   Already OK  : {skipped} entries (already 128-dim)")
    print()
    print("[Migrate] Your local memory.db is now compatible with the new embeddings.")
    print("[Migrate] Next step: push memory.db to Render or use a hosted database.")

if __name__ == "__main__":
    migrate()
