import logging

from hr_buddy.app.services.llm_service import LLMService
from hr_buddy.app.services.retrieval_service import (
    RetrievalService
)
from hr_buddy.app.models.requests import RAGConfig
from hr_buddy.app.core.query_logger import save_query_response


logger = logging.getLogger(__name__)


class ChatService:

    def __init__(self):

        self.llm = LLMService()

        self.retrieval = (
            RetrievalService()
        )

    def _apply_rag_config(self, rag_config: RAGConfig):
        """Refresh the retrieval pipeline so the current request settings are used."""
        if (
            rag_config.chunk_size != self.retrieval.chunk_size
            or rag_config.chunk_overlap != self.retrieval.chunk_overlap
        ):
            self.retrieval = RetrievalService(
                chunk_size=rag_config.chunk_size,
                chunk_overlap=rag_config.chunk_overlap,
            )

    def ask(self, question, rag_config: RAGConfig | None = None):

        logger.info(
            "Processing HR question"
        )

        # Use provided config or defaults
        if rag_config is None:
            rag_config = RAGConfig()

        self._apply_rag_config(rag_config)

        results = (
            self.retrieval.search(
                question,
                top_k=rag_config.top_k
            )
        )

        if not results:

            answer = (
                "I could not find "
                "relevant information "
                "in the HR knowledge base."
            )
            save_query_response(
                question=question,
                answer=answer,
                sources=[],
                chunk_size=rag_config.chunk_size,
                chunk_overlap=rag_config.chunk_overlap,
                top_k=rag_config.top_k,
            )
            return {
                "answer": answer,
                "sources": []
            }

        context = "\n\n".join(
            result["content"]
            for result in results
        )

        answer = self.llm.generate(
            question,
            context
        )

        sources = []

        for result in results:

            sources.append(
                {
                    "document": result[
                        "document"
                    ],
                    "page": None,
                    "content": result[
                        "content"
                    ],
                    "score": result[
                        "score"
                    ]
                }
            )

        save_query_response(
            question=question,
            answer=answer,
            sources=sources,
            chunk_size=rag_config.chunk_size,
            chunk_overlap=rag_config.chunk_overlap,
            top_k=rag_config.top_k,
        )

        return {
            "answer": answer,
            "sources": sources
        }