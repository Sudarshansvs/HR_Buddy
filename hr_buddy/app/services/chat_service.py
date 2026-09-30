import logging

from hr_buddy.app.services.llm_service import LLMService
from hr_buddy.app.services.retrieval_service import (
    RetrievalService
)


logger = logging.getLogger(__name__)


class ChatService:

    def __init__(self):

        self.llm = LLMService()

        self.retrieval = (
            RetrievalService()
        )

    def ask(self, question):

        logger.info(
            "Processing HR question"
        )

        results = (
            self.retrieval.search(
                question
            )
        )

        if not results:

            return {
                "answer": (
                    "I could not find "
                    "relevant information "
                    "in the HR knowledge base."
                ),
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

        return {
            "answer": answer,
            "sources": sources
        }