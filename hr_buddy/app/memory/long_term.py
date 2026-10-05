import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from hr_buddy.app.core.config import settings
from hr_buddy.app.rag.embeddings import EmbeddingService


logger = logging.getLogger(__name__)


# New facts this similar to an existing one are treated as duplicates
DUPLICATE_THRESHOLD = 0.9


class LongTermMemory:
    """Facts about each employee, persisted to JSON and searched by embedding."""

    def __init__(self, path: str = None):

        self.path = Path(path or settings.LONG_TERM_MEMORY_PATH)

        self.embedder = EmbeddingService()

        self._lock = threading.Lock()

        self._data: dict[str, list[dict]] = self._load()

    def _load(self) -> dict:

        if not self.path.exists():
            return {}

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.error("Corrupt long-term memory file: %s", self.path)
            return {}

        return data if isinstance(data, dict) else {}

    def _save(self):

        self.path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        tmp_path.replace(self.path)

    def add(self, user_id: str, facts: list[str]) -> list[dict]:
        """Store new facts for a user, skipping near-duplicates. Returns what was added."""

        facts = [fact.strip() for fact in facts if fact and fact.strip()]

        if not user_id or not facts:
            return []

        embeddings = self.embedder.embed(facts)

        added = []

        with self._lock:
            memories = self._data.setdefault(user_id, [])

            for fact, embedding in zip(facts, embeddings):

                if any(
                    float(np.dot(embedding, memory["embedding"])) >= DUPLICATE_THRESHOLD
                    for memory in memories
                ):
                    continue

                memory = {
                    "id": uuid.uuid4().hex,
                    "text": fact,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "embedding": [float(value) for value in embedding]
                }
                memories.append(memory)
                added.append(memory)

            if added:
                self._save()

        logger.info("Stored %s long-term memories for user %s", len(added), user_id)

        return added

    def search(self, user_id: str | None, query: str, top_k: int = None, min_score: float = None) -> list[dict]:
        """Return the user's memories most relevant to the query."""

        top_k = top_k or settings.LONG_TERM_TOP_K
        min_score = settings.LONG_TERM_MIN_SCORE if min_score is None else min_score

        with self._lock:
            memories = list(self._data.get(user_id, [])) if user_id else []

        if not memories:
            return []

        query_embedding = self.embedder.embed([query])[0]

        matrix = np.array([memory["embedding"] for memory in memories], dtype="float32")
        scores = matrix @ query_embedding

        ranked = sorted(
            zip(scores, memories),
            key=lambda pair: pair[0],
            reverse=True
        )

        return [
            {
                "id": memory["id"],
                "text": memory["text"],
                "score": float(score)
            }
            for score, memory in ranked[:top_k]
            if min_score is None or score >= min_score
        ]

    def list(self, user_id: str) -> list[dict]:

        with self._lock:
            return [
                {
                    "id": memory["id"],
                    "text": memory["text"],
                    "created_at": memory["created_at"]
                }
                for memory in self._data.get(user_id, [])
            ]

    def delete(self, user_id: str, memory_id: str) -> bool:

        with self._lock:
            memories = self._data.get(user_id, [])
            remaining = [memory for memory in memories if memory["id"] != memory_id]

            if len(remaining) == len(memories):
                return False

            self._data[user_id] = remaining
            self._save()

        return True

    def clear(self, user_id: str):

        with self._lock:
            if self._data.pop(user_id, None) is not None:
                self._save()
