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


settings = Settings()