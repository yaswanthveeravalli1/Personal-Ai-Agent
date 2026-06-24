from database import init_db, add_entry, get_all_entries, delete_entries
from embeddings import embed, cosine_sim

init_db()
TOP_K = 6

def add_memory(user_id, entry, section):
    embedding = embed(entry)
    return add_entry(user_id, section, entry, embedding)

def get_relevant_memory(user_id, query, top_k=TOP_K):
    entries = get_all_entries(user_id)
    if not entries:
        return "No memory yet."
    query_emb = embed(query)
    scored = [(cosine_sim(query_emb, emb), section, entry) for section, entry, emb in entries]
    scored.sort(reverse=True, key=lambda x: x[0])
    return "\n".join(f"[{section}] {entry}" for _, section, entry in scored[:top_k])

def forget(user_id, keyword):
    return delete_entries(user_id, keyword) > 0
