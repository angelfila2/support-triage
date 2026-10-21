from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from backend.rag import vector


class CountingEmbeddings(Embeddings):
    def __init__(self):
        self.embedded = []

    def embed_documents(self, texts):
        self.embedded.extend(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 0.0, 0.0]


def test_restart_reuses_embeddings_and_document_updates_replace_stale_content(tmp_path, monkeypatch):
    embedding = CountingEmbeddings()
    monkeypatch.setattr(vector, "CHROMA_DIR", tmp_path / "index")
    monkeypatch.setattr(vector, "OllamaEmbeddings", lambda **kwargs: embedding)
    old = Document(page_content="Old FAQ", metadata={"source": "faq.md"})
    first = vector.create_vector_store([old])
    assert len(first.get()["ids"]) == 1
    assert embedding.embedded == ["Old FAQ"]
    restarted = vector.create_vector_store([old])
    assert len(restarted.get()["ids"]) == 1
    assert embedding.embedded == ["Old FAQ"]
    new = Document(page_content="New FAQ", metadata={"source": "faq.md"})
    updated = vector.create_vector_store([new])
    assert updated.get()["documents"] == ["New FAQ"]
    assert embedding.embedded == ["Old FAQ", "New FAQ"]
