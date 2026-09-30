import logging

from hr_buddy.app.rag.loader import DocumentLoader
from hr_buddy.app.rag.chunker import TextChunker
from hr_buddy.app.rag.retriever import Retriever
from hr_buddy.app.core.config import settings


logger = logging.getLogger(__name__)


class RetrievalService:

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):

        self.loader = DocumentLoader(
            settings.DOCUMENTS_PATH
        )

        # Use provided config or defaults from settings
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        self.chunker = TextChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

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

    def search(self, question, top_k: int = None):

        if top_k is None:
            top_k = settings.TOP_K

        return self.retriever.retrieve(
            question,
            top_k
        )