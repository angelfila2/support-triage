import os
import math
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
def _resolve_path(name: str, default: Path) -> Path:
    """Resolve relative overrides from backend/, independent of the launch folder."""
    value = os.getenv(name)
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


OUTPUT_DIR = _resolve_path("OUTPUT_DIR", BASE_DIR / "output")
TICKETS_FILE = _resolve_path("TICKETS_FILE", OUTPUT_DIR / "tickets_processed.csv")
KNOWLEDGE_BASE_DIR = _resolve_path("KNOWLEDGE_BASE_DIR", BASE_DIR / "knowledgebase")
CHROMA_DIR = _resolve_path("CHROMA_DIR", BASE_DIR / "chroma_db")
DATA_DIR = _resolve_path("DATA_DIR", BASE_DIR / "data")
SAMPLE_TICKETS_FILE = _resolve_path("SAMPLE_TICKETS_FILE", DATA_DIR / "sample_tickets.csv")
TRIAGE_RESULTS_FILE = _resolve_path("TRIAGE_RESULTS_FILE", OUTPUT_DIR / "triage_results.csv")

# Ollama / Model Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))
TRIAGE_TIMEOUT_SECONDS = float(os.getenv("TRIAGE_TIMEOUT_SECONDS", "120"))
MAX_CONCURRENT_TRIAGE = int(os.getenv("MAX_CONCURRENT_TRIAGE", "2"))
if (not all(math.isfinite(value) and value > 0 for value in (OLLAMA_TIMEOUT_SECONDS, TRIAGE_TIMEOUT_SECONDS))
        or MAX_CONCURRENT_TRIAGE <= 0):
    raise ValueError("Inference timeouts and concurrency must be positive.")

# CORS Origins
_default_cors = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _default_cors).split(",")
    if origin.strip()
]

# Ensure output directory exists automatically
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
