"""Versioned evidence snapshots for each immutable triage attempt."""

import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from time import monotonic
from urllib.request import urlopen

from backend.config import KNOWLEDGE_BASE_DIR, OLLAMA_BASE_URL, OLLAMA_MODEL

_manifest_cache = (0, [])


def ollama_models(timeout=2):
    with urlopen(OLLAMA_BASE_URL.rstrip("/") + "/api/tags", timeout=timeout) as response:
        return json.load(response)["models"]


def provenance():
    global _manifest_cache
    now = monotonic()
    if now - _manifest_cache[0] > 60:
        try:
            _manifest_cache = (now, ollama_models())
        except (OSError, ValueError, KeyError):
            _manifest_cache = (now, [])
    names = {name if ":" in name else name + ":latest" for name in (OLLAMA_MODEL, "mxbai-embed-large")}
    files = sorted((Path(__file__).parent / "agent").glob("*.py"))
    files += sorted((Path(__file__).parent / "rag").glob("*.py"))
    return {
        "model": OLLAMA_MODEL, "embedding_model": "mxbai-embed-large",
        "model_digests": {row["name"]: row.get("digest") for row in _manifest_cache[1] if row["name"] in names},
        "model_digest_available": any(row["name"] == (OLLAMA_MODEL if ":" in OLLAMA_MODEL else OLLAMA_MODEL + ":latest") for row in _manifest_cache[1]),
        "code_sha256": {str(path.relative_to(Path(__file__).parent)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        "knowledge_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))},
        "packages": {name: version(name) for name in ("langchain-ollama", "langchain-chroma", "pydantic")},
    }


def evidence_snapshot(sources):
    # Only allow known filenames; a model-returned path never controls file access.
    known = {path.name: path for path in KNOWLEDGE_BASE_DIR.glob("*.md")}
    evidence = []
    for source in dict.fromkeys(sources):
        name = str(source).replace("\\", "/").rsplit("/", 1)[-1]
        if name in known:
            content = known[name].read_text(encoding="utf-8")
            evidence.append({"source": name, "content": content,
                             "sha256": hashlib.sha256(content.encode()).hexdigest()})
    return evidence
