from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma


def create_vector_store(documents):

    embeddings = OllamaEmbeddings(
        model="mxbai-embed-large"
    )

    vector_store = Chroma(
        collection_name="support_knowledge_base",
        embedding_function=embeddings
    )

    vector_store.add_documents(documents)

    return vector_store