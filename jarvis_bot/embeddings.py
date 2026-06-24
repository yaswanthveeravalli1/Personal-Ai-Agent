import numpy as np
import hashlib

def stable_hash(word):
    return int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)

def embed(text):
    # Lightweight deterministic keyword hash-trick representation
    vector = np.zeros(128, dtype=np.float32)
    words = text.lower().split()
    for w in words:
        idx = stable_hash(w) % 128
        vector[idx] += 1.0
    return vector

def cosine_sim(a, b):
    if len(a) != len(b):
        # Handle dimension mismatch gracefully (e.g. if database contains old embeddings of different size)
        return 0.0
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(a, b) / (norm_a * norm_b + 1e-8)
