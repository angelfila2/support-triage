from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

try:
    from config import OLLAMA_BASE_URL
except ImportError:
    OLLAMA_BASE_URL = "http://localhost:11434"


def create_vector_store(documents):
    embeddings = OllamaEmbeddings(
        model="mxbai-embed-large",
        base_url=OLLAMA_BASE_URL
    )

    vector_store = Chroma(
        collection_name="support_knowledge_base",
        embedding_function=embeddings
    )

    vector_store.add_documents(documents)

    return vector_store