from pathlib import Path
from typing import List

from pypdf import PdfReader


class DocumentLoader:

    def __init__(self, documents_path: str):

        self.documents_path = Path(
            documents_path
        )

    def _extract_pdf_text(self, file_path: Path) -> str:

        try:
            reader = PdfReader(str(file_path))
            pages = []
            for p in reader.pages:
                try:
                    pages.append(p.extract_text() or "")
                except Exception:
                    pages.append("")
            return "\n\n".join(pages)
        except Exception:
            return ""

    def load_documents(self) -> List[dict]:

        documents = []

        # support .txt, .md and .pdf files
        for ext in ("*.txt", "*.md", "*.pdf"):

            for file_path in self.documents_path.glob(ext):

                if file_path.suffix.lower() == ".pdf":

                    content = self._extract_pdf_text(file_path)

                else:

                    content = file_path.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )

                documents.append(
                    {
                        "document": file_path.name,
                        "content": content
                    }
                )

        return documents