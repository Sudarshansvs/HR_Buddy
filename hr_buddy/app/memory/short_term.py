import threading
from collections import deque

from hr_buddy.app.core.config import settings


class ShortTermMemory:
    """Recent conversation turns per chat session, kept in process memory."""

    def __init__(self, max_turns: int = None):

        self.max_turns = max_turns or settings.SHORT_TERM_MAX_TURNS

        self._sessions: dict[str, deque] = {}

        self._lock = threading.Lock()

    def get(self, session_id: str | None) -> list[dict]:
        """Return turns as [{"question": ..., "answer": ...}], oldest first."""

        if not session_id:
            return []

        with self._lock:
            return list(self._sessions.get(session_id, []))

    def add(self, session_id: str | None, question: str, answer: str):

        if not session_id:
            return

        with self._lock:
            turns = self._sessions.setdefault(
                session_id,
                deque(maxlen=self.max_turns)
            )
            turns.append(
                {
                    "question": question,
                    "answer": answer
                }
            )

    def clear(self, session_id: str):

        with self._lock:
            self._sessions.pop(session_id, None)
