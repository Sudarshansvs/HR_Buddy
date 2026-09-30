import json
from pathlib import Path

from hr_buddy.app.core.config import settings


def _get_query_log_path() -> Path:
    log_path = Path(settings.QUERY_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text("[]", encoding="utf-8")
    return log_path


def save_query_response(
    question: str,
    answer: str,
    sources: list[dict] | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    top_k: int | None = None,
):
    """Save a single Q&A interaction as JSON metadata."""
    sources = sources or []

    log_entry = {
        "chunk_size": chunk_size if chunk_size is not None else settings.CHUNK_SIZE,
        "chunk_overlap": chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP,
        "top_k": top_k if top_k is not None else settings.TOP_K,
        "user_query": question,
        "citation_document_names_with_scores": [
            {
                "document": item.get("document"),
                "score": item.get("score"),
            }
            for item in sources
        ],
        "response_from_llm_first_50_words": " ".join((answer or "").split()[:50]),
        "response": answer,
    }

    log_path = _get_query_log_path()
    with log_path.open("r", encoding="utf-8") as file:
        try:
            logs = json.load(file)
        except json.JSONDecodeError:
            logs = []

    if not isinstance(logs, list):
        logs = []

    logs.append(log_entry)

    with log_path.open("w", encoding="utf-8") as file:
        json.dump(logs, file, indent=2, ensure_ascii=False)
