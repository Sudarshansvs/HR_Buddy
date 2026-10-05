import logging
import threading
from dataclasses import dataclass, field

from hr_buddy.app.services.llm_service import LLMService
from hr_buddy.app.services.retrieval_service import (
    RetrievalService
)
from hr_buddy.app.services.task_service import (
    TASK_INTENTS,
    get_task_service
)
from hr_buddy.app.models.requests import RAGConfig, LLMConfig
from hr_buddy.app.core.query_logger import save_query_response
from hr_buddy.app.memory import (
    get_long_term_memory,
    get_short_term_memory
)


logger = logging.getLogger(__name__)


NO_RESULTS_ANSWER = (
    "I could not find "
    "relevant information "
    "in the HR knowledge base."
)


@dataclass
class Plan:
    """How to answer one message.

    reply set:        a fixed answer (task result or no results); the LLM isn't called.
    context None:     conversation, answered with the conversation prompt.
    context set:      policy question, answered from the retrieved documents.
    new_facts None:   facts not extracted yet, so extract them after answering.
    """

    history: list[dict]

    memories: list[str]

    sources: list[dict] = field(default_factory=list)

    context: str | None = None

    reply: str | None = None

    card: dict | None = None

    new_facts: list[str] | None = None


class ChatService:

    def __init__(self):

        self.llm = LLMService()

        self.retrieval = (
            RetrievalService()
        )

        self.short_term = get_short_term_memory()

        self.long_term = get_long_term_memory()

        self.tasks = get_task_service()

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

    def _classify(self, question) -> str:

        try:
            return self.llm.classify_intent(question)
        except Exception:
            logger.exception("Intent classification failed; treating as HR question")
            return "hr_question"

    def _plan(self, question, rag_config: RAGConfig, document, session_id, user_id, history) -> Plan:

        self._apply_rag_config(rag_config)

        if history is None:
            history = self.short_term.get(session_id)
        else:
            history = history[-self.short_term.max_turns:]

        memories = [
            memory["text"]
            for memory in self.long_term.search(user_id, question)
        ]

        # A half-finished task (e.g. leave dates still missing) takes the next message first
        result = self.tasks.continue_draft(question, user_id, session_id)

        if result is None:
            intent = self._classify(question)
            logger.info("Message intent: %s", intent)

            if intent in TASK_INTENTS:
                result = self.tasks.handle(intent, question, user_id, session_id)

        else:
            intent = "task"

        if result is not None:
            return Plan(history, memories, reply=result.text, card=result.card)

        if intent == "conversation":
            # Extract facts before replying so the reply knows exactly what is new
            new_facts = self._extract_facts(question)

            if user_id and new_facts:
                self.long_term.add(user_id, new_facts)

            memories += [fact for fact in new_facts if fact not in memories]

            return Plan(history, memories, new_facts=new_facts)

        # Follow-ups like "what about sick leave?" need the previous question to retrieve well
        search_query = (
            f"{history[-1]['question']}\n{question}"
            if history
            else question
        )

        results = (
            self.retrieval.search(
                search_query,
                top_k=rag_config.top_k,
                # document filter (None means search all documents)
                document=document,
            )
        )

        if not results:
            return Plan(history, memories, reply=NO_RESULTS_ANSWER)

        sources = [
            {
                "document": result["document"],
                "page": None,
                "content": result["content"],
                "score": result["score"]
            }
            for result in results
        ]

        context = "\n\n".join(
            result["content"]
            for result in results
        )

        return Plan(history, memories, sources=sources, context=context)

    def _extract_facts(self, question) -> list[str]:

        try:
            return self.llm.extract_facts(question)
        except Exception:
            logger.exception("Failed to extract facts")
            return []

    def _finish(self, question, answer, plan: Plan, rag_config: RAGConfig, session_id, user_id):
        """Log the interaction and update both memories."""

        save_query_response(
            question=question,
            answer=answer,
            sources=plan.sources,
            chunk_size=rag_config.chunk_size,
            chunk_overlap=rag_config.chunk_overlap,
            top_k=rag_config.top_k,
        )

        self.short_term.add(session_id, question, answer)

        if user_id and plan.new_facts is None:
            # Fact extraction is a second LLM call; keep it off the response path
            threading.Thread(
                target=self._update_long_term,
                args=(user_id, question),
                daemon=True
            ).start()

    def _update_long_term(self, user_id, question):

        try:
            self.long_term.add(user_id, self._extract_facts(question))
        except Exception:
            logger.exception("Failed to update long-term memory")

    def ask(self, question, rag_config: RAGConfig | None = None, llm_config: LLMConfig | None = None, document: str | None = None, session_id: str | None = None, user_id: str | None = None, history: list[dict] | None = None):

        logger.info(
            "Processing HR question"
        )

        # Use provided config or defaults
        if rag_config is None:
            rag_config = RAGConfig()

        if llm_config is None:
            llm_config = LLMConfig()

        plan = self._plan(
            question, rag_config, document, session_id, user_id, history
        )

        if plan.reply is not None:
            answer = plan.reply
        else:
            answer = self.llm.generate(
                question,
                plan.context,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                top_p=llm_config.top_p,
                frequency_penalty=llm_config.frequency_penalty,
                presence_penalty=llm_config.presence_penalty,
                history=plan.history,
                memories=plan.memories,
                new_facts=plan.new_facts
            )

        self._finish(question, answer, plan, rag_config, session_id, user_id)

        return {
            "answer": answer,
            "sources": plan.sources,
            "card": plan.card
        }

    def ask_stream(self, question, rag_config: RAGConfig | None = None, llm_config: LLMConfig | None = None, document: str | None = None, session_id: str | None = None, user_id: str | None = None, history: list[dict] | None = None):
        """Yield events: "sources", then "token"s, then an optional "card", then "done"."""

        logger.info(
            "Processing HR question (streaming)"
        )

        if rag_config is None:
            rag_config = RAGConfig()

        if llm_config is None:
            llm_config = LLMConfig()

        plan = self._plan(
            question, rag_config, document, session_id, user_id, history
        )

        yield {"type": "sources", "sources": plan.sources, "memories": plan.memories}

        if plan.reply is not None:
            answer = plan.reply
            yield {"type": "token", "content": answer}
        else:
            parts = []
            for token in self.llm.generate_stream(
                question,
                plan.context,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                top_p=llm_config.top_p,
                history=plan.history,
                memories=plan.memories,
                new_facts=plan.new_facts
            ):
                parts.append(token)
                yield {"type": "token", "content": token}

            answer = "".join(parts)

        if plan.card:
            yield {"type": "card", "card": plan.card}

        self._finish(question, answer, plan, rag_config, session_id, user_id)

        yield {"type": "done"}
