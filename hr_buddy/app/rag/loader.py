from pathlib import Path


class DocumentLoader:

    def __init__(self, documents_path: str):

        self.documents_path = Path(
            documents_path
        )

    def load_documents(self):

        documents = []

        for file_path in self.documents_path.glob("*.txt"):

            content = file_path.read_text(
                encoding="utf-8"
            )

            documents.append(
                {
                    "document": file_path.name,
                    "content": content
                }
            )

        return documents