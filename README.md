# HR Buddy

HR Buddy is a simple HR assistant app that lets users ask HR-related questions through a Streamlit frontend and gets answers from a local FastAPI + Ollama backend.

## Features

- Streamlit UI for asking questions
- FastAPI API backend
- Local LLM integration using Ollama
- Simple startup script to run both services together

## Project structure

- `app.py` - Streamlit frontend
- `llm_test_2.py` - FastAPI backend with Ollama integration
- `run.py` - Starts both backend and frontend
- `requirements.txt` - Python dependencies
- `prompt.py` - prompt definitions

## Prerequisites

- Python 3.10+
- Ollama installed and running locally
- An Ollama model available, such as `llama3.2:3b`

## Install dependencies

```bash
pip install -r requirements.txt
```

## Start Ollama

Make sure Ollama is running in the background and the model is available.

Example:

```bash
ollama pull llama3.2:3b
```

## Run the app

From the project folder:

```bash
python run.py
```

This starts:
- the backend at `http://127.0.0.1:8080`
- the frontend at the default Streamlit URL

## Use the app

Open the Streamlit page in the browser and ask an HR-related question.

## Notes

This app is designed for local use and does not invent company policies. It responds conservatively when information is missing.
