import logging

import ollama

from hr_buddy.app.core.config import settings
from hr_buddy.app.prompts.hr_prompt import SYSTEM_PROMPT


logger = logging.getLogger(__name__)


class LLMService:

    def __init__(self):

        self.client = ollama.Client(
            host=settings.OLLAMA_HOST
        )

        self.model = settings.LLM_MODEL

    def generate_deprecated(
        self,
        question: str,
        context: str
    ) -> str:

        prompt = SYSTEM_PROMPT.format(
            question=question,
            context=context
        )

        logger.info(
            "Calling LLM model: %s",
            self.model
        )

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                }
            ]
        )

        return response["message"]["content"]


    def generate(
            self,
            question: str,
            context: str
        ) -> str:   

        prompt = SYSTEM_PROMPT.format(
                    question=question,
                    context=context
                )

        logger.info(
                    "Calling LLM model: %s",
                    self.model
                )
        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response["message"]["content"]