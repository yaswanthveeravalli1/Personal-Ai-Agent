from google import genai
import numpy as np
import hashlib
import config

def get_gemini_client():
    if not config.GEMINI_API_KEY or "YOUR_GEMINI_API_KEY" in config.GEMINI_API_KEY:
        return None
    try:
        return genai.Client(api_key=config.GEMINI_API_KEY)
    except Exception:
        return None

def stable_hash(word):
    return int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)

def embed(text):
    client = get_gemini_client()
    if client:
        try:
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            return np.array(response.embeddings[0].values, dtype=np.float32)
        except Exception as e:
            print(f"[Embeddings] Gemini embedding API failed: {e}. Falling back to deterministic keyword representation.", flush=True)
    
    # Fallback: stable hash-trick vectorizer
    vector = np.zeros(128, dtype=np.float32)
    words = text.lower().split()
    for w in words:
        idx = stable_hash(w) % 128
        vector[idx] += 1.0
    return vector

def cosine_sim(a, b):
    if len(a) != len(b):
        # Handle dimension mismatch gracefully (e.g. if switching between fallback and API embeddings,
        # or if database contains old 384-dim embeddings from sentence-transformers)
        return 0.0
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(a, b) / (norm_a * norm_b + 1e-8)
