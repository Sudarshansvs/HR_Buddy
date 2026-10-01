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
            context: str,
            temperature: float = 0.7,
            max_tokens: int = 500,
            top_p: float = 0.9,
            frequency_penalty: float = 0.0,
            presence_penalty: float = 0.0
        ) -> str:   

        prompt = SYSTEM_PROMPT.format(
                    question=question,
                    context=context
                )

        logger.info(
                    "Calling LLM model: %s with temperature=%s, max_tokens=%s, top_p=%s",
                    self.model,
                    temperature,
                    max_tokens,
                    top_p
                )
        
        # Build options dict with tuning parameters
        options = {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens
        }
        
        # Note: Ollama/Llama models may not support all parameters
        # frequency_penalty and presence_penalty are not directly supported
        # but can be approximated through prompt engineering if needed
        
        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options=options
        )

        return response["message"]["content"]