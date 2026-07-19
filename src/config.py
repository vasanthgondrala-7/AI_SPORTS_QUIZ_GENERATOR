import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_PROVIDER = "gemini" if GEMINI_API_KEY else "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1"
ENABLE_LIVE_SEARCH = os.getenv("ENABLE_LIVE_SEARCH", "1") == "1"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chromadb")
MAX_DB_RESULTS = int(os.getenv("MAX_DB_RESULTS", "3"))

if not OPENAI_API_KEY and not GEMINI_API_KEY and not MOCK_MODE:
    print("[WARNING] No LLM API key found. Set OPENAI_API_KEY or GEMINI_API_KEY in .env, or enable MOCK_MODE=1 for demo.")
