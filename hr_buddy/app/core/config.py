import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


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

    TOP_K: int = int(
        os.getenv("TOP_K", "5")
    )

    CHUNK_SIZE: int = int(
        os.getenv("CHUNK_SIZE", "500")
    )

    CHUNK_OVERLAP: int = int(
        os.getenv("CHUNK_OVERLAP", "100")
    )

    DOCUMENTS_PATH: str = os.getenv(
        "DOCUMENTS_PATH",
        str(PROJECT_ROOT / "hr_buddy" / "data" / "documents")
    )

    VECTOR_DB_PATH: str = os.getenv(
        "VECTOR_DB_PATH",
        str(PROJECT_ROOT / "hr_buddy" / "data" / "vector_db")
    )


settings = Settings()