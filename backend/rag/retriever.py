"""Retrieve FAQ documents that meet a minimum relevance score."""


def create_retriever(
    vector_store,
    k: int = 2,
    score_threshold: float = 0.5,
):
    """Return up to k documents that pass the relevance threshold."""

    if k < 1:
        raise ValueError("k must be at least 1.")

    if not 0.0 <= score_threshold <= 1.0:
        raise ValueError("score_threshold must be between 0 and 1.")

    return vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": k,
            "score_threshold": score_threshold,
        },
    )


def retrieve_documents(retriever, query: str):
    """Return matching documents, or an empty list if none qualify."""

    return retriever.invoke(query)