from hr_buddy.app.rag.embeddings import EmbeddingService
from hr_buddy.app.rag.vector_store import VectorStore


class Retriever:

    def __init__(self):

        self.embedding_service = (
            EmbeddingService()
        )

        self.vector_store = VectorStore()

    def build_index(self, documents):

        texts = [
            doc["content"]
            for doc in documents
        ]

        embeddings = (
            self.embedding_service.embed(
                texts
            )
        )

        self.vector_store.build(
            embeddings,
            documents
        )

    def retrieve(
        self,
        question,
        top_k=5,
        document: str | None = None
    ):

        embedding = (
            self.embedding_service.embed(
                [question]
            )[0]
        )

        results = self.vector_store.search(
            embedding,
            top_k
        )

        if document:

            # Filter results to only include chunks coming from the specified document
            results = [r for r in results if r.get("document") == document]

        return results

    def add_embeddings(self, texts, documents):
        """Incrementally add new text chunks with their metadata.

        texts: list of strings to embed
        documents: list of metadata dicts (should match len(texts))
        """
        if not texts:
            return

        embeddings = (
            self.embedding_service.embed(texts)
        )

        self.vector_store.add(
            embeddings,
            documents
        )