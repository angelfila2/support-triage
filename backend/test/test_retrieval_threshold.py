"""Test LangChain threshold filtering without calling an embedding service."""

import pytest
import chromadb
from uuid import uuid4
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

from backend.rag.retriever import create_retriever, retrieve_documents
from backend.rag import vector


class FixedEmbeddings(Embeddings):
    """Known vectors isolate threshold behavior from model quality."""

    def embed_documents(self, texts):
        vectors = {"Password reset instructions": [1.0, 0.0, 0.0],
                   "Invoice instructions": [0.0, 1.0, 0.0]}
        return [vectors[text] for text in texts]

    def embed_query(self, text):
        return {"reset": [1.0, 0.0, 0.0], "unrelated": [0.0, 0.0, 1.0],
                "opposite": [-1.0, 0.0, 0.0]}[text]


@pytest.fixture
def store(monkeypatch):
    # Exercise the production factory, replacing only external embeddings
    # and the collection identity so tests cannot touch application documents.
    monkeypatch.setattr(vector, "OllamaEmbeddings", lambda **kwargs: FixedEmbeddings())

    def isolated_chroma(**kwargs):
        kwargs["collection_name"] = "test_" + uuid4().hex
        kwargs.pop("persist_directory", None)
        return Chroma(client=chromadb.EphemeralClient(), **kwargs)

    monkeypatch.setattr(vector, "Chroma", isolated_chroma)
    store = vector.create_vector_store([
        Document(page_content="Password reset instructions"),
        Document(page_content="Invoice instructions"),
    ])
    yield store
    store.delete_collection()


def test_threshold_removes_weak_match_instead_of_filling_k(store):
    retriever = create_retriever(store)
    documents = retrieve_documents(retriever, "reset")
    assert [document.page_content for document in documents] == ["Password reset instructions"]


def test_nothing_qualifying_returns_empty_list(store):
    assert retrieve_documents(create_retriever(store), "unrelated") == []


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan")])
def test_invalid_threshold_is_rejected(store, threshold):
    with pytest.raises(ValueError, match="score_threshold"):
        create_retriever(store, score_threshold=threshold)


@pytest.mark.parametrize("k", [0, -1])
def test_invalid_limit_is_rejected(store, k):
    with pytest.raises(ValueError, match="k must"):
        create_retriever(store, k=k)


def test_custom_threshold_and_limit_are_used(store):
    documents = retrieve_documents(create_retriever(store, k=1, score_threshold=0.9), "reset")
    assert len(documents) == 1
    assert documents[0].page_content == "Password reset instructions"


@pytest.mark.parametrize(("distance", "expected"), [
    (0.0, 1.0), (0.3, 0.7), (1.0, 0.0), (1.5, 0.0),
    (2.0, 0.0), (-0.000001, 1.0),
])
def test_cosine_score_conversion_and_clipping(distance, expected):
    assert vector.cosine_relevance_score(distance) == pytest.approx(expected)


def test_chroma_uses_cosine_metric_and_bounded_scores(store):
    assert store._collection.configuration["hnsw"]["space"] == "cosine"
    for query in ("reset", "unrelated", "opposite"):
        matches = store.similarity_search_with_relevance_scores(query, k=2)
        assert len(matches) == 2
        assert all(0.0 <= score <= 1.0 for _, score in matches)
    assert retrieve_documents(create_retriever(store), "opposite") == []
