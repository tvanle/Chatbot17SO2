# Chatbot17SO2

A RAG-powered chatbot for answering questions about PTIT (Posts and Telecommunications Institute of Technology), built as PTIT coursework.

## Features

- Authentication and chat/message management API (`BE/`, FastAPI, `/api/auth/*` and `/api/chat/*`)
- RAG pipeline (`Chatbot/`): document ingestion, chunking, embeddings, vector retrieval and LLM answer generation (`/api/rag/*`)
- Domain-specific RAG services for admission, tuition, regulations and general questions, plus a domain router
- Optional Redis cache for the RAG pipeline
- Flask data management service (`DataManagment/`) for file upload and web crawling
- Vanilla JavaScript chat frontend (`FE/`)
- Knowledge base of PTIT documents in `Chatbot/assets/raw/`

## Tech stack

- Python, FastAPI, Flask, SQLAlchemy (SQLite by default, MySQL optional)
- OpenAI API for generation, sentence-transformers for embeddings
- Qdrant vector database, Redis cache
- Docker and docker-compose files included

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                # add OPENAI_API_KEY and service settings
python -m uvicorn BE.main:app --reload --port 8000  # backend + RAG on port 8000
cd FE && python -m http.server 8080                 # frontend
```

Optional: `python DataManagment/main.py` starts the Flask data service on port 5000.
See `Chatbot/README.md` and `Chatbot/ARCHITECTURE.md` for the RAG design.
