import logging

from hr_buddy.app.rag.loader import DocumentLoader
from hr_buddy.app.rag.chunker import TextChunker
from hr_buddy.app.rag.retriever import Retriever
from hr_buddy.app.core.config import settings


logger = logging.getLogger(__name__)


class RetrievalService:

    def __init__(self):

        self.loader = DocumentLoader(
            settings.DOCUMENTS_PATH
        )

        self.chunker = TextChunker()

        self.retriever = Retriever()

        self.initialize()

    def initialize(self):

        try:
            documents = (
                self.loader.load_documents()
            )
        except Exception as e:
            logger.error("Failed to load documents from %s: %s", settings.DOCUMENTS_PATH, e)
            return

        chunks = []

        for document in documents:

            document_chunks = (
                self.chunker.split(
                    document["content"]
                )
            )

            for chunk in document_chunks:

                chunks.append(
                    {
                        "document": document[
                            "document"
                        ],
                        "content": chunk
                    }
                )

        if not documents:
            logger.error("No documents found in %s. Please ensure document files exist in this directory.", settings.DOCUMENTS_PATH)
            return

        if not chunks:
            logger.error("Documents loaded, but no chunks were created. Check document content and chunking settings.")
            return

        try:
            self.retriever.build_index(chunks)
            logger.info("Indexed %s chunks from %s documents", len(chunks), len(documents))
        except Exception as e:
            logger.error("Failed to build vector index: %s", e)

    def search(self, question):

        return self.retriever.retrieve(
            question,
            settings.TOP_K
        )