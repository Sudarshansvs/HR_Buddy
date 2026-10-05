import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Use the repository root, not the package directory, as the base path
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "HR Buddy")

    LLM_MODEL: str = os.getenv(
        "LLM_MODEL",
        "llama3.2:3b"
    )

    OLLAMA_HOST: str = os.getenv(
        "OLLAMA_HOST",
        "http://localhost:11434"
    )

    DOCUMENTS_PATH: str = os.getenv(
        "DOCUMENTS_PATH",
        str(PROJECT_ROOT / "data" / "documents")
    )

    VECTOR_DB_PATH: str = os.getenv(
        "VECTOR_DB_PATH",
        str(PROJECT_ROOT / "data" / "vector_db")
    )

    TOP_K: int = int(
        os.getenv("TOP_K", "5")
    )

    CHUNK_SIZE: int = int(
        os.getenv("CHUNK_SIZE", "500")
    )

    CHUNK_OVERLAP: int = int(
        os.getenv("CHUNK_OVERLAP", "100")
    )

    QUERY_LOG_PATH: str = os.getenv(
        "QUERY_LOG_PATH",
        str(PROJECT_ROOT / "data" / "query_logs.json")
    )

    # Local mock HR system (leave balances, requests, tickets)
    HR_DB_PATH: str = os.getenv(
        "HR_DB_PATH",
        str(PROJECT_ROOT / "data" / "hr_system.sqlite3")
    )

    # Short-term memory: recent turns kept per chat session
    SHORT_TERM_MAX_TURNS: int = int(
        os.getenv("SHORT_TERM_MAX_TURNS", "5")
    )

    # Long-term memory: facts about each employee, persisted across sessions
    LONG_TERM_MEMORY_PATH: str = os.getenv(
        "LONG_TERM_MEMORY_PATH",
        str(PROJECT_ROOT / "data" / "memory" / "long_term.json")
    )

    # Facts about one person are few and relevant in non-obvious ways
    # (location matters for a relocation question), so by default every
    # fact is used and similarity only ranks them once there are more than TOP_K
    LONG_TERM_TOP_K: int = int(
        os.getenv("LONG_TERM_TOP_K", "8")
    )

    # Unset by default: cosine scores can be negative for facts that still matter
    LONG_TERM_MIN_SCORE: float | None = (
        float(os.environ["LONG_TERM_MIN_SCORE"])
        if os.getenv("LONG_TERM_MIN_SCORE")
        else None
    )


settings = Settings()
