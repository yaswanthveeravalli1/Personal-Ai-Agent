import json
import time
import httpx
from memory import get_relevant_memory, add_memory
import config

COMBINED_PROMPT = """You are Jarvis, a helpful personal assistant with memory.

Relevant memory about this user:
{memory}

User message:
{message}

Respond ONLY with valid JSON, no markdown formatting, no extra text:
{{
  "reply": "your natural reply to the user",
  "memory_entries": [
    {{"section": "Preferences" | "Facts" | "Tasks", "entry": "short factual statement"}}
  ]
}}

Only include memory_entries if there is genuinely new info worth remembering. Otherwise return an empty list.
"""

MAX_RETRIES = 2  # Lowered slightly to speed up failover transitions


def _call_gemini(prompt):
    """Call Gemini API using google-genai SDK."""
    if not config.GEMINI_API_KEY or "YOUR_GEMINI_API_KEY" in config.GEMINI_API_KEY:
        return None
    from google import genai
    from google.genai import errors as genai_errors

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    model = "gemini-2.0-flash"

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except genai_errors.ClientError as e:
            if "429" in str(e) and attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                print(f"[Jarvis] Gemini rate limited, retrying in {wait}s...", flush=True)
                time.sleep(wait)
            else:
                return None
        except Exception as e:
            print(f"[Jarvis] Gemini error: {e}", flush=True)
            return None
    return None


def _call_openrouter(prompt):
    """Call OpenRouter API (free models available)."""
    if not config.OPENROUTER_API_KEY or "YOUR_OPENROUTER_API_KEY" in config.OPENROUTER_API_KEY:
        return None
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/google/antigravity",
        "X-Title": "Jarvis Bot",
    }
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    print(f"[Jarvis] OpenRouter rate limited, retrying in {wait}s...", flush=True)
                    time.sleep(wait)
                    continue
                else:
                    return None
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Jarvis] OpenRouter error: {e}", flush=True)
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
            else:
                return None
    return None


def _call_ollama(prompt):
    """Call a local Ollama instance (100% free and offline)."""
    url = f"{config.OLLAMA_HOST}/v1/chat/completions"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[Jarvis] Ollama error: {e}", flush=True)
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
            else:
                return None
    return None


def _call_groq(prompt):
    """Call Groq API with automatic model rotation across all free models.
    If one model hits a rate limit, immediately tries the next model."""
    if not config.GROQ_API_KEY or "YOUR_GROQ_API_KEY" in config.GROQ_API_KEY:
        return None

    # All Groq chat models (excludes whisper/audio-only and guard models)
    GROQ_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "qwen/qwen3-32b",
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "allam-2-7b",
    ]

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for model in GROQ_MODELS:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        try:
            print(f"[Jarvis] Trying Groq model: {model}...", flush=True)
            resp = httpx.post(url, json=payload, headers=headers, timeout=25)
            if resp.status_code == 429:
                print(f"[Jarvis] Groq {model} rate limited, trying next model...", flush=True)
                continue
            if resp.status_code != 200:
                print(f"[Jarvis] Groq {model} returned {resp.status_code}, trying next...", flush=True)
                continue
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"[Jarvis] ✅ Groq {model} responded successfully!", flush=True)
            return content
        except Exception as e:
            print(f"[Jarvis] Groq {model} error: {e}, trying next...", flush=True)
            continue

    print("[Jarvis] All Groq models exhausted.", flush=True)
    return None


def _call_ai(prompt):
    """Route to the configured AI provider, falling back automatically if it fails."""
    # Define routing map
    call_methods = {
        "groq": _call_groq,
        "gemini": _call_gemini,
        "openrouter": _call_openrouter,
        "ollama": _call_ollama,
    }

    # Put primary provider at the start of our lookup chain
    primary = config.AI_PROVIDER
    fallbacks = [p for p in ["groq", "gemini", "openrouter", "ollama"] if p != primary]
    execution_chain = [primary] + fallbacks

    for provider in execution_chain:
        call_fn = call_methods.get(provider)
        if call_fn:
            print(f"[Jarvis] Attempting inference via {provider.upper()}...", flush=True)
            result = call_fn(prompt)
            if result is not None:
                # Successfully received response, return it
                if provider != primary:
                    print(f"[Jarvis] Fallback to {provider.upper()} was successful!", flush=True)
                return result
            print(f"[Jarvis] {provider.upper()} failed or is unconfigured. Trying fallback...", flush=True)

    return None


def generate_reply(user_id, message):
    memory = get_relevant_memory(user_id, message)
    prompt = COMBINED_PROMPT.format(memory=memory, message=message)

    raw = _call_ai(prompt)
    if raw is None:
        return "⚠️ All configured AI services are temporarily unavailable. Please try again in a moment."

    try:
        cleaned = raw.strip().strip("`").replace("json", "", 1).strip()
        data = json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError):
        return raw  # fallback if model didn't return clean JSON

    for item in data.get("memory_entries", []):
        if item.get("entry"):
            add_memory(user_id, item["entry"], item.get("section", "Facts"))

    return data.get("reply", "Sorry, I couldn't process that.")
