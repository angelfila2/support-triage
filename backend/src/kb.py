from pathlib import Path

from langchain_core.documents import Document


def load_knowledge_base(folder_path):
    documents = []

    folder = Path(folder_path)

    for file_path in folder.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")

        document = Document(
            page_content=content,
            metadata={
                "source": file_path.name
            }
        )

        documents.append(document)

    return documents