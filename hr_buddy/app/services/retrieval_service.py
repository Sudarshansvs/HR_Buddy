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

    def search(self, question, top_k: int = None, document: str | None = None):

        if top_k is None:
            top_k = settings.TOP_K

        # Accept optional document filter from callers
        return self.retriever.retrieve(
            question,
            top_k,
            document=document
        )

    def add_documents(self, documents):
        """Incrementally add new documents to the index.

        documents: list of dicts with keys 'document' (name) and 'content' (text)
        """
        if not documents:
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
                        "document": document.get("document", "unknown"),
                        "content": chunk
                    }
                )

        if chunks:
            texts = [c["content"] for c in chunks]
            self.retriever.add_embeddings(texts, chunks)
            logger.info("Added %s new chunks to index", len(chunks))

    def delete_document(self, document_name: str) -> int:
        """Delete all chunks from a specific document.

        document_name: name of the document
        returns: number of chunks deleted
        """
        deleted_count = self.retriever.vector_store.delete_by_document(document_name)
        logger.info("Deleted %s chunks for document: %s", deleted_count, document_name)
        return deleted_count

    def delete_chunk(self, chunk_id: int) -> bool:
        """Delete a specific chunk by its ID.

        chunk_id: index of the chunk to delete
        returns: True if successful, False otherwise
        """
        success = self.retriever.vector_store.delete_by_index(chunk_id)
        if success:
            logger.info("Deleted chunk %d", chunk_id)
        else:
            logger.warning("Failed to delete chunk %d", chunk_id)
        return success

    def update_chunk(self, chunk_index: int, new_text: str, document_name: str) -> bool:
        """Update a chunk's content and re-embed it.

        chunk_index: index of chunk to update
        new_text: new content for the chunk
        document_name: document name for metadata
        returns: True if successful
        """
        try:
            # Re-embed the new text
            new_embedding = self.retriever.embedding_service.embed([new_text])[0]

            # Create new document dict with updated content
            new_doc = {
                "document": document_name,
                "content": new_text
            }

            # Update in vector store
            success = self.retriever.vector_store.update_chunk(chunk_index, new_embedding, new_doc)

            if success:
                logger.info("Updated chunk %d", chunk_index)
            else:
                logger.warning("Failed to update chunk %d (out of range)", chunk_index)

            return success
        except Exception as e:
            logger.error("Error updating chunk %d: %s", chunk_index, e)
            return False

    def clear_index(self):
        """Clear all documents from the index."""
        self.retriever.vector_store.clear()
        logger.info("Cleared all documents from index")

    def get_index_info(self) -> dict:
        """Get statistics about the current index."""
        return self.retriever.vector_store.get_info()

    def get_chunk(self, chunk_id: int) -> dict | None:
        """Get a chunk by its ID."""
        return self.retriever.vector_store.get_chunk(chunk_id)