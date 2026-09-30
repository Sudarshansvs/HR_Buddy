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
        top_k=5
    ):

        embedding = (
            self.embedding_service.embed(
                [question]
            )[0]
        )

        return self.vector_store.search(
            embedding,
            top_k
        )