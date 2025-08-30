import os
from dotenv import load_dotenv

# Load variables from a local .env if present (safe to run even if .env is missing)
load_dotenv()

# --- API / models ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-8b-8192")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# --- Paths ---
TRANSCRIPTS_DIR = "transcripts"   # where your .txt files live
PERSIST_DIR     = "data/chroma"   # Chroma will persist its index here

# --- Chunking ---
MAX_CHARS = 1500                  # target ~1200–1500 chars per chunk
