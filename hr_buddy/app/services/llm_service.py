import json
import logging
from collections.abc import Iterator
from datetime import date, timedelta

import ollama

from hr_buddy.app.core.config import settings
from hr_buddy.app.prompts.hr_prompt import (
    CONVERSATION_PROMPT,
    INTENT_PROMPT,
    INTENTS,
    LEAVE_DATES_PROMPT,
    MEMORY_EXTRACTION_PROMPT,
    NEW_FACTS_RULE,
    NO_NEW_FACTS_RULE,
    SYSTEM_PROMPT
)


logger = logging.getLogger(__name__)


class LLMService:

    def __init__(self):

        self.client = ollama.Client(
            host=settings.OLLAMA_HOST
        )

        self.model = settings.LLM_MODEL

    def _build_messages(
            self,
            question: str,
            context: str | None,
            history: list[dict] | None = None,
            memories: list[str] | None = None,
            new_facts: list[str] | None = None
        ) -> list[dict]:
        """Put memories and earlier turns inside the prompt; small models follow that better than chat history.

        A context of None means the message is conversation, not a policy question.
        """

        history_text = "\n\n".join(
            f"Employee: {turn['question']}\nHR Buddy: {turn['answer']}"
            for turn in history or []
        )

        fields = {
            "question": question,
            "memories": "\n".join(f"- {memory}" for memory in memories or []) or "None",
            "history": history_text or "None"
        }

        if context is None:
            new_facts_rule = (
                NEW_FACTS_RULE.format(facts=" ".join(new_facts))
                if new_facts
                else NO_NEW_FACTS_RULE
            )
            prompt = CONVERSATION_PROMPT.format(new_facts_rule=new_facts_rule, **fields)
        else:
            prompt = SYSTEM_PROMPT.format(context=context, **fields)

        return [{"role": "user", "content": prompt}]

    def generate(
            self,
            question: str,
            context: str | None,
            temperature: float = 0.7,
            max_tokens: int = 500,
            top_p: float = 0.9,
            frequency_penalty: float = 0.0,
            presence_penalty: float = 0.0,
            history: list[dict] | None = None,
            memories: list[str] | None = None,
            new_facts: list[str] | None = None
        ) -> str:

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

        response = self.client.chat(
            model=self.model,
            messages=self._build_messages(question, context, history, memories, new_facts),
            options=options
        )

        return response["message"]["content"]

    def generate_stream(
            self,
            question: str,
            context: str | None,
            temperature: float = 0.7,
            max_tokens: int = 500,
            top_p: float = 0.9,
            history: list[dict] | None = None,
            memories: list[str] | None = None,
            new_facts: list[str] | None = None
        ) -> Iterator[str]:
        """Yield the answer token-by-token as Ollama produces it."""

        logger.info(
                    "Streaming LLM model: %s with temperature=%s, max_tokens=%s, top_p=%s",
                    self.model,
                    temperature,
                    max_tokens,
                    top_p
                )

        options = {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": max_tokens
        }

        stream = self.client.chat(
            model=self.model,
            messages=self._build_messages(question, context, history, memories, new_facts),
            options=options,
            stream=True
        )

        for chunk in stream:
            content = chunk["message"]["content"]
            if content:
                yield content

    def extract_facts(self, question: str) -> list[str]:
        """Pull durable facts the employee stated about themselves out of their message."""

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": MEMORY_EXTRACTION_PROMPT.format(question=question)
                }
            ],
            format="json",
            options={"temperature": 0.0}
        )

        try:
            facts = json.loads(response["message"]["content"]).get("facts", [])
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Memory extraction returned invalid JSON")
            return []

        # Small models invent facts; keep only those backed by a real quote from the message
        message = question.lower()
        grounded = []

        for item in facts:
            if not isinstance(item, dict):
                continue

            fact = item.get("fact")
            quote = item.get("quote")

            if (
                isinstance(fact, str)
                and isinstance(quote, str)
                and quote.strip()
                and quote.strip().lower() in message
            ):
                grounded.append(fact)
            else:
                logger.info("Dropped ungrounded memory: %s", item)

        return grounded

    def classify_intent(self, question: str) -> str:
        """Return one of INTENTS; falls back to "hr_question".

        The previous message is deliberately left out: the 3B model copies its
        intent ("what's my balance?" then "apply annual leave..." became a balance check).
        """

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": INTENT_PROMPT.format(question=question)
                }
            ],
            format="json",
            options={"temperature": 0.0, "num_predict": 20}
        )

        try:
            intent = json.loads(response["message"]["content"]).get("intent")
        except (json.JSONDecodeError, AttributeError):
            intent = None

        return intent if intent in INTENTS else "hr_question"

    def extract_leave_dates(self, question: str, today: date) -> tuple[date, date] | None:
        """Resolve explicit dates like "12th to 14th October" with a calendar in the prompt."""

        calendar = "\n".join(
            f"{day:%a %d %b %Y} = {day.isoformat()}"
            for day in (today + timedelta(days=offset) for offset in range(-7, 60))
        )

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": LEAVE_DATES_PROMPT.format(
                        today=f"{today:%A %d %B %Y}",
                        calendar=calendar,
                        question=question
                    )
                }
            ],
            format="json",
            options={"temperature": 0.0, "num_predict": 60}
        )

        try:
            dates = json.loads(response["message"]["content"])
            start = dates.get("start_date") or dates.get("end_date")
            end = dates.get("end_date") or start
            if not start:
                return None
            return date.fromisoformat(start), date.fromisoformat(end)
        except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
            logger.warning("Leave date extraction returned invalid output")
            return None
