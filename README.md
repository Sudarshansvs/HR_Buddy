# HR Buddy

HR Buddy is an HR knowledge assistant built with a FastAPI backend, Streamlit frontend, and a local retrieval-augmented generation (RAG) pipeline powered by Ollama and sentence embeddings.

It helps employees ask HR questions such as leave policies, onboarding guidance, and internal procedures using the documents stored in the project data folder.
demo :  https://www.youtube.com/watch?v=qAEcApqlN6M
## Features

- Streamlit UI for chat-based HR Q&A
- FastAPI API with health and chat routes
- Retrieval-augmented generation using document chunks and vector search
- Adjustable RAG settings for chunk size, overlap, and top-k results
- Local Ollama LLM integration
- Query logging to JSON for debugging and experimentation
- Document-aware HR knowledge base from local text files

## Architecture

- `hr_buddy/app/main.py` - FastAPI application entry point
- `hr_buddy/app/api/` - API routes for chat, health, and documents
- `hr_buddy/app/services/` - business logic for chat and retrieval
- `hr_buddy/app/rag/` - document loading, chunking, embeddings, and vector retrieval
- `hr_buddy/app/core/` - configuration, logging, and query logging
- `hr_buddy/frontend/streamlit_app.py` - user-facing chat interface
- `run.py` - starts the backend and frontend together
- `data/documents/` - source HR documents used in retrieval
- `data/query_logs.json` - logged prompts and responses

## Project structure

```text
HR_Buddy/
├── README.md
├── requirements.txt
├── run.py
├── data/
│   ├── documents/
│   │   ├── leave_policy.txt
│   │   └── onboarding.txt
│   ├── vector_db/
│   └── query_logs.json
├── hr_buddy/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── prompts/
│   │   ├── rag/
│   │   └── services/
│   └── frontend/
│       └── streamlit_app.py
└── tests/
```

## Prerequisites

- Python 3.10+
- Ollama installed and running locally
- An Ollama model available, for example:

```bash
ollama pull llama3.2:3b
```

## Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment configuration

The app reads configuration from environment variables and falls back to defaults if missing. Relevant settings include:

- `APP_NAME`
- `LLM_MODEL`
- `OLLAMA_HOST`
- `DOCUMENTS_PATH`
- `VECTOR_DB_PATH`
- `TOP_K`
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `QUERY_LOG_PATH`

Example:

```bash
export LLM_MODEL="llama3.2:3b"
export OLLAMA_HOST="http://localhost:11434"
export CHUNK_SIZE="500"
export CHUNK_OVERLAP="100"
export TOP_K="5"
```

## Run the application

From the project root:

```bash
python run.py
```

This starts:

- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:8501`

## API endpoints

### Health check

```bash
curl http://localhost:8000/health
```

### Chat endpoint

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the leave policy?",
    "rag_config": {
      "chunk_size": 500,
      "chunk_overlap": 100,
      "top_k": 5
    }
  }'
```

## Frontend usage

Open the Streamlit app in the browser at:

```text
http://localhost:8501
```

Use the sidebar controls to adjust:

- Chunk Size
- Chunk Overlap
- Top K Results

These values are sent with each chat request and are also stored in the query log.

## Query logging

Each interaction is stored in `data/query_logs.json` with metadata including:

- `chunk_size`
- `chunk_overlap`
- `top_k`
- `user_query`
- `citation_document_names_with_scores`
- `response`

This is useful for analyzing retrieval quality and debugging chunking behavior.

## Notes

- The project is designed for local use and local document retrieval.
- The system intentionally responds conservatively when relevant HR information is not found.
- For production-like deployments, you would typically add authentication, caching, monitoring, and a stronger ingestion pipeline.

## Troubleshooting

If the app does not start correctly:

1. Make sure Ollama is running.
2. Confirm your model is downloaded using `ollama list`.
3. Ensure dependencies are installed with `pip install -r requirements.txt`.
4. Check the backend logs or run the app in the terminal for detailed errors.
