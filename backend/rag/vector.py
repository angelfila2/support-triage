"""Create the FAQ vector store with explicit cosine relevance scoring."""

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from hashlib import sha256

from backend.config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT_SECONDS, CHROMA_DIR


def cosine_relevance_score(distance: float) -> float:
    """Convert cosine distance into nonnegative cosine similarity."""

    similarity = 1.0 - distance

    # Negative similarity means the vectors point away from each other.
    # Clamp the score to the range expected by our retriever.
    return max(0.0, min(1.0, similarity))


def create_vector_store(documents):
    if not documents:
        raise ValueError("Knowledge base is empty.")
    embeddings = OllamaEmbeddings(
        model="mxbai-embed-large",
        base_url=OLLAMA_BASE_URL,
        client_kwargs={"timeout": OLLAMA_TIMEOUT_SECONDS},
    )

    vector_store = Chroma(
        # Use a distinct collection so an older distance configuration
        # cannot accidentally be reused.
        collection_name="support_knowledge_base_cosine_v2",
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_configuration={
            "hnsw": {
                "space": "cosine",
            },
        },
        relevance_score_fn=cosine_relevance_score,
    )

    # Content-addressed IDs avoid duplicate documents and unnecessary embeddings.
    wanted = {sha256((str(doc.metadata.get("source", "")) + "\0" + doc.page_content).encode()).hexdigest(): doc
              for doc in documents}
    existing = set(vector_store.get(include=[])["ids"])
    missing = sorted(set(wanted) - existing)
    if missing:
        vector_store.add_documents([wanted[key] for key in missing], ids=missing)
    stale = sorted(existing - set(wanted))
    if stale:
        vector_store.delete(ids=stale)

    return vector_store
