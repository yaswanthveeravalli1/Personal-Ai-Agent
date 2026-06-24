import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter").lower()

# Gemini config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OpenRouter config
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-4b-it:free")

# Ollama config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Groq config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not TELEGRAM_TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN in .env file")

if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env file")

if AI_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
    raise ValueError("Missing OPENROUTER_API_KEY in .env file. Get one free at https://openrouter.ai/keys")

if AI_PROVIDER == "groq" and not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env file")
