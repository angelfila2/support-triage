import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent


def _load_env_file(filepath: Path) -> None:
    """Lightweight fallback .env loader when python-dotenv is not installed."""
    if not filepath.is_file():
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


# Attempt to load environment variables from .env files
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    _load_env_file(BASE_DIR / ".env")
    _load_env_file(REPO_ROOT / ".env")

# Directory and File Paths
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output")).resolve()
TICKETS_FILE = Path(
    os.getenv("TICKETS_FILE", OUTPUT_DIR / "tickets_processed.csv")
).resolve()
KNOWLEDGE_BASE_DIR = Path(
    os.getenv("KNOWLEDGE_BASE_DIR", BASE_DIR / "knowledgebase")
).resolve()
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
SAMPLE_TICKETS_FILE = Path(
    os.getenv("SAMPLE_TICKETS_FILE", DATA_DIR / "sample_tickets.csv")
).resolve()
TRIAGE_RESULTS_FILE = Path(
    os.getenv("TRIAGE_RESULTS_FILE", OUTPUT_DIR / "triage_results.csv")
).resolve()

# Ollama / Model Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# CORS Origins
_default_cors = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _default_cors).split(",")
    if origin.strip()
]

# Ensure output directory exists automatically
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
