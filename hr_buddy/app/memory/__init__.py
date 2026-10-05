from functools import lru_cache

from hr_buddy.app.memory.long_term import LongTermMemory
from hr_buddy.app.memory.short_term import ShortTermMemory


# Shared instances so the chat and memory routes see the same state

@lru_cache(maxsize=1)
def get_short_term_memory() -> ShortTermMemory:
    return ShortTermMemory()


@lru_cache(maxsize=1)
def get_long_term_memory() -> LongTermMemory:
    return LongTermMemory()
