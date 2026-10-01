import sys
import pathlib
import importlib
import numpy as np

# Ensure the project root is on sys.path so `hr_buddy` imports resolve under pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient


class FakeEmbeddingService:
    def __init__(self, model_name=None):
        pass

    def embed(self, texts):
        # deterministic, low-dimension embeddings (len-based)
        arr = np.array([[float(len(t))] * 8 for t in texts], dtype="float32")
        return arr


class FakeLLMService:
    def __init__(self):
        pass

    def generate(self, question: str, context: str) -> str:
        return f"FAKE_ANSWER: {question}"


def setup_module():
    """Replace heavy external services with fakes before importing the app."""

    # Monkeypatch embedding and LLM services used during app import
    import hr_buddy.app.rag.embeddings as emb_mod
    import hr_buddy.app.services.llm_service as llm_mod

    emb_mod.EmbeddingService = FakeEmbeddingService
    llm_mod.LLMService = FakeLLMService


def test_upload_text_and_query():
    # import app after monkeypatching
    from hr_buddy.app.main import app

    client = TestClient(app)

    filename = "test_doc.txt"
    content = "This is a test document about HR policies. Vacation policy: two weeks."

    files = {"file": (filename, content.encode("utf-8"), "text/plain")}

    resp = client.post("/api/v1/documents/upload", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["filename"] == filename
    assert "Vacation policy" in data["preview"]

    # Query the uploaded document only
    payload = {
        "question": "What is the vacation policy?",
        "rag_config": None,
        "document": filename,
    }

    resp2 = client.post("/api/v1/chat", json=payload)
    assert resp2.status_code == 200, resp2.text
    j = resp2.json()

    # Basic shape assertions
    assert "answer" in j and "sources" in j

    # If the fake LLM was used and retrieval produced context, we expect our fake answer.
    # Otherwise, the service may return the 'could not find relevant information' fallback.
    if j["answer"].startswith("FAKE_ANSWER"):
        assert True
    else:
        assert j["answer"].startswith("I could not find")

    # If any sources were returned, ensure they reference the uploaded filename
    if j.get("sources"):
        assert any(s["document"] == filename for s in j.get("sources", []))
