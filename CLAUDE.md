# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Chatbot17SO2** is a RAG-powered chatbot system for PTIT (Posts and Telecommunications Institute of Technology) information consulting. The system combines authentication, chat management, RAG-based question answering with OpenAI, and data management services.

**Tech Stack**: FastAPI (backend), Flask (data service), vanilla JavaScript (frontend), SQLAlchemy ORM, SQLite/MySQL database, OpenAI API, sentence-transformers for embeddings.

## Architecture

The project follows a **3-tier MVC architecture with DAO pattern**, split into four main modules:

### 1. BE (Backend Service)
Authentication, chat management, and user management service.
- **Models**: User, Chat, Message, Model
- **Controllers**: Auth (`/api/auth/*`), Chat (`/api/chat/*`)
- **Services**: authService, chatService
- **DAO**: UserDAO, ChatDAO, MessageDAO, ModelDAO
- **Database**: SQLite (default) or MySQL via SQLAlchemy

### 2. Chatbot (RAG System)
Retrieval-Augmented Generation system with vector search and LLM integration.

**Key Architecture** (defined in `Chatbot/kichban.txt` PlantUML diagrams):
- **ERD**: documents (1) → chunks (*) → embeddings (1:1)
- **Services**:
  - `VectorizerService`: Text → Vector embedding (sentence-transformers)
  - `RetrieverService`: Vector search + chunk/document hydration
  - `GeneratorService`: LLM-based answer generation
  - `ModelClient`: LLM API client (OpenAI/Anthropic)
- **DAO**: DocumentDAO, ChunkDAO, VectorIndexDAO
- **Controllers**: RAGController (`/api/rag/*`)

**RAG Flow**:
1. **Answer**: Vectorize question → Search vector index → Hydrate chunks/docs → Generate answer with LLM → Return with citations
2. **Ingest**: Upsert document → Split into chunks → Embed chunks → Store vectors

### 3. DataManagment (Data Processing)
**Note the typo**: The directory is spelled `DataManagment/` (not `DataManagement/`). This is the actual working directory containing the Flask service code.

Flask-based data management service for document uploads and web crawling.
- **Port**: 5000 (Flask default)
- **Models**: User, FileData, CrawledData
- **Controllers**: FileDataDAO, CrawledDataDAO, StatisticDAO
- **Features**: File upload (DOCX, TXT), web crawling, statistics tracking

### 4. FE (Frontend)
Vanilla JavaScript SPA with modular ES6 architecture.
- **Structure**:
  - `js/main.js` - Entry point
  - `js/apiService.js` - HTTP client for backend APIs
  - `js/chatManager.js` - Chat business logic
  - `js/uiManager.js` - DOM manipulation and UI updates
  - `js/auth.js` - Authentication flows
  - `js/config.js` - API endpoints and DOM element references
- **Pages**: `index.html` (chat interface), `login.html` (auth)
- **Serving**: Use Python HTTP server (`python -m http.server 8080`) or VSCode Live Server (port 5500)

## Common Commands

### Development Setup

```bash
# 1. Create and activate virtual environment (recommended)
python -m venv .venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 4. Database is auto-created on first run (SQLite by default)
```

### Running Services

**All-in-One: Backend + RAG Service (Port 8000)**:
```bash
# Both BE and Chatbot services run together via BE/main.py
python -m uvicorn BE.main:app --reload --port 8000

# The RAG endpoints are available at /api/rag/*
# Backend endpoints are at /api/auth/* and /api/chat/*
```

**DataManagement Service (Flask - Port 5000)** - Optional:
```bash
# Only needed if you want to upload files or crawl websites
python DataManagment/main.py
```

**Frontend**:
```bash
# Option 1: Python HTTP server
cd FE && python -m http.server 8080

# Option 2: VSCode Live Server (recommended for hot reload)
# Right-click FE/index.html → "Open with Live Server"
# Runs on http://127.0.0.1:5500
```

**Quick Start (Minimal Setup)**:
```bash
# Terminal 1: Backend
python -m uvicorn BE.main:app --reload --port 8000

# Terminal 2: Frontend
cd FE && python -m http.server 8080

# Open browser: http://127.0.0.1:8080
```

### Database

**Default: SQLite** (`./chatbot.db` in root)

**Switch to MySQL**:
```bash
# Set environment variable
export USE_SQLITE=false
export DB_USER=root
export DB_PASS=yourpassword
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=chatbot
```

**Initialize database** (auto-created on app startup):
```bash
# Tables are created automatically via SQLAlchemy
python -m uvicorn BE.main:app --reload
# Check: curl http://127.0.0.1:8000/health
```

### Testing

**Health checks**:
```bash
# Backend health
curl http://127.0.0.1:8000/health

# RAG system health
curl http://127.0.0.1:8000/api/rag/health
```

**Test RAG ingest**:
```bash
curl -X POST http://127.0.0.1:8000/api/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "namespace_id": "ptit_docs",
    "document_title": "Test Document",
    "content": "PTIT là Học viện Công nghệ Bưu chính Viễn thông..."
  }'
```

**Test RAG query**:
```bash
curl -X POST http://127.0.0.1:8000/api/rag/answer \
  -H "Content-Type: application/json" \
  -d '{
    "namespace_id": "ptit_docs",
    "question": "PTIT là gì?",
    "top_k": 3,
    "token_budget": 1000
  }'
```

## Configuration

### RAG Configuration
File: [Chatbot/config/rag_config.py](Chatbot/config/rag_config.py)

**Key settings**:
- `embedding_model`: `"sentence-transformers/all-MiniLM-L6-v2"` (384 dim)
- `llm_backend`: `"openai"` (requires `OPENAI_API_KEY` env var)
- `llm_model`: `"gpt-3.5-turbo"`
- `chunk_size`: 512 characters
- `chunk_overlap`: 50 characters
- `default_top_k`: 5 chunks
- `default_token_budget`: 2000 tokens

**Environment variables**:
```bash
# Required for LLM generation
export OPENAI_API_KEY=sk-...
# OR
export ANTHROPIC_API_KEY=sk-ant-...
```

### CORS Configuration
File: [BE/core/config.py](BE/core/config.py)

Allowed origins:
- `http://127.0.0.1:5500` (VSCode Live Server)
- `http://127.0.0.1:3000`
- `http://127.0.0.1:8080` (Python HTTP Server)
- `null` (for file:// protocol)

## Key Implementation Details

### Service Integration Architecture
The system uses a **monolithic deployment** where both BE and Chatbot modules run in the same FastAPI process (via `BE/main.py`), but they are architecturally separated as different routers:
- `BE/controllers/auth.py` → `/api/auth/*`
- `BE/controllers/chat.py` → `/api/chat/*`
- `Chatbot/controllers/RAGController.py` → `/api/rag/*` (imported in BE/main.py)

The chat service calls RAG via internal function calls (not HTTP), treating RAG as a library/module.

### RAG Controller Logic
**Critical Design Decision**: All RAG orchestration logic is in [Chatbot/controllers/RAGController.py](Chatbot/controllers/RAGController.py) - there is **NO separate RAGService layer**. The controller directly orchestrates:
- `VectorizerService` - Text to vector embeddings
- `RetrieverService` - Vector similarity search
- `GeneratorService` - LLM answer generation via OpenAI

This violates typical 3-tier architecture but was chosen to reduce complexity for this project.

### Service Singletons
`VectorizerService` and `GeneratorService` are **singleton instances** in RAGController (using global variables `_vectorizer_service` and `_generator_service`). This is critical for performance - loading sentence-transformers models is expensive (~1-2 seconds), so we load once at startup.

### Database Schema Relationships
```
documents (1) ──< chunks (many)
chunks (1) ──── embeddings (1)
```
- **documents**: Source documents with metadata (title, source_uri, namespace)
- **chunks**: Text segments (512 chars default) split from documents
- **embeddings**: 384-dimensional vectors (one per chunk)

All models inherit from `Base` (SQLAlchemy declarative base) and are registered via `Base.metadata.create_all()` in [BE/main.py](BE/main.py:30).

### Critical Directory Naming Issue
There are TWO directories with similar names:
- `DataManagement/` - Empty except for requirements.txt (DO NOT USE)
- `DataManagment/` - **The actual Flask service code** (USE THIS)

This typo is baked into the codebase. Always use `DataManagment/` when working with the data management service.

### Message Processing Flow
Understanding the complete flow from user input to AI response:

1. **User submits message** in [FE/index.html](FE/index.html)
2. `ChatManager.sendMessage()` → `ApiService.sendMessage()`
3. `POST /api/chat/send` → [BE/controllers/chat.py](BE/controllers/chat.py)
4. [BE/services/chatService.py](BE/services/chatService.py):
   - Saves user message to database via `MessageDAO`
   - Calls RAG controller's `answer_question()` function directly (internal call, not HTTP)
5. [Chatbot/controllers/RAGController.py](Chatbot/controllers/RAGController.py):
   - `VectorizerService.embed()` - Convert question to vector
   - `RetrieverService.retrieve()` - Search vector database for similar chunks
   - `GeneratorService.generate()` - Call OpenAI API with context
6. [Chatbot/services/ModelClient.py](Chatbot/services/ModelClient.py):
   - Makes HTTPS POST to `https://api.openai.com/v1/chat/completions`
   - Receives response from GPT-3.5-turbo
7. Response flows back through services to controller
8. Chat service saves bot message to database
9. Returns JSON response to frontend
10. `UIManager.displayMessage()` renders bot response

**Key insight**: The RAG service is NOT a separate HTTP microservice - it's a Python module imported and called directly by the chat service.

## API Endpoints Reference

### Authentication (`/api/auth/*`)
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration

### Chat (`/api/chat/*`)
- `POST /api/chat/create` - Create new chat
- `GET /api/chat/list?user_id={id}` - List user's chats
- `GET /api/chat/messages?chat_id={id}` - Get chat messages
- `POST /api/chat/send` - Send message & get bot response
- `GET /api/chat/models` - List available models

### RAG (`/api/rag/*`)
- `POST /api/rag/answer` - Answer question with RAG
- `POST /api/rag/ingest` - Ingest document into vector store
- `GET /api/rag/documents` - List documents (with pagination)
- `GET /api/rag/documents/{doc_id}` - Get document details
- `DELETE /api/rag/documents/{doc_id}` - Delete document
- `GET /api/rag/health` - RAG system health check

### Data Management (Flask - Port 5000)
- `POST /api/uploadfile` - Upload document
- `GET /api/filedata` - List uploaded files
- `GET /api/filedata/{file_id}` - Get file details
- `GET /api/crawleddata` - List crawled web data
- `GET /api/statistic` - Get statistics

## Dependencies

The root [requirements.txt](requirements.txt) contains ALL dependencies for both BE and Chatbot modules:

**Web Framework**:
- `fastapi==0.120.0` - Main REST API framework
- `uvicorn==0.38.0` - ASGI server
- `python-multipart==0.0.20` - File upload support

**Database**:
- `sqlalchemy==2.0.44` - ORM for database operations
- `pymysql==1.1.2` - MySQL driver (optional, only if not using SQLite)
- `cryptography==46.0.3` - For password hashing

**AI/RAG**:
- `openai==2.6.1` - **CRITICAL** - OpenAI API client for GPT models
- `numpy==2.3.4` - Vector operations
- `sentence-transformers` - **NOT IN requirements.txt** - You need to add this if doing embeddings
- `torch` - **NOT IN requirements.txt** - PyTorch backend for sentence-transformers

**HTTP & Configuration**:
- `requests==2.31.0` - HTTP client
- `httpx==0.28.1` - Async HTTP client
- `python-dotenv==1.2.1` - Environment variable management
- `pydantic==2.12.3` - Data validation

**Missing Dependencies** (mentioned in docs but not in requirements.txt):
```bash
# If you need to actually use RAG embeddings, install:
pip install sentence-transformers torch

# Optional performance improvements:
pip install faiss-cpu  # Faster vector search
pip install tiktoken   # Better tokenization for OpenAI models
```

**DataManagment Service** (Flask):
The Flask service has its own dependencies. Check [DataManagment/main.py](DataManagment/main.py) for imports:
- `flask`
- `flask-cors`
- `python-docx` (for DOCX file parsing)

## Development Notes

- The project uses Vietnamese language for documentation and UI
- Default namespace for documents is `"ptit_docs"`
- Frontend uses mock data in `FE/js/config.js` for development
- The embedding model supports multilingual text (Vietnamese + English)
- Database auto-initializes on first startup via SQLAlchemy `create_all()`

## Production Considerations

As noted in [Chatbot/README.md](Chatbot/README.md), for production:
1. Use Pinecone/Weaviate instead of database vector store
2. Deploy local LLM (Llama 3, Mistral) to reduce costs
3. Add Redis cache for frequently asked questions
4. Implement monitoring for latency, token usage, error rates
5. Add rate limiting and JWT authentication

## Project-Specific Development Rules

### Architecture Constraints

**Follow 3-Tier MVC + DAO Pattern** (with RAG Controller exception):
- **Controller** → HTTP endpoints only, minimal logic
- **Service** → Business logic (except RAG - see note below)
- **DAO** → Database queries only
- **Model** → SQLAlchemy ORM classes

**RAG Exception**: `RAGController` contains all orchestration logic directly - there is no `RAGService`. When modifying RAG features, all logic goes in the controller.

### Code Organization Rules

**Module Placement**:
- Auth/user features → `BE/controllers/auth.py`, `BE/services/authService.py`, `BE/dao/UserDAO.py`
- Chat features → `BE/controllers/chat.py`, `BE/services/chatService.py`, `BE/dao/ChatDAO.py`, `BE/dao/MessageDAO.py`
- RAG features → `Chatbot/controllers/RAGController.py` (no service layer), `Chatbot/services/*` (supporting services), `Chatbot/dao/*`
- Data management → `DataManagment/` (note the typo)

**Naming Conventions**:
- Python: `snake_case` for functions/variables, `PascalCase` for classes
- JavaScript: `camelCase` for functions/variables, `PascalCase` for classes
- Database tables: `tblModelName` (e.g., `tblUser`, `tblChat`)
- DAO classes: `ModelNameDAO` (e.g., `UserDAO`, `DocumentDAO`)

### File Creation Policy

**Do NOT create** unless explicitly requested:
- Documentation files (`*.md`, `README.md`, `GUIDE.md`, `TODO.md`)
- Shell scripts (`*.sh`, `*.bash`)
- Configuration templates
- Migration files (use SQLAlchemy auto-create)

**Do create**:
- Model classes when adding new database entities
- DAO classes for new models
- Service classes for new business logic domains
- Controller routes for new API endpoints

### Database Changes

- **Schema changes**: Modify Model classes, then restart server (auto-creates tables)
- **DO NOT** use Alembic migrations unless explicitly requested
- **DO NOT** write raw SQL - use SQLAlchemy ORM
- Default database is SQLite (`chatbot.db` in root) - automatically created on first run

### Dependency Management

**Root `requirements.txt`**: Contains all dependencies for BE + Chatbot (unified install)
- When adding dependencies, add to root `requirements.txt` with pinned versions
- Format: `package==version` (e.g., `fastapi==0.120.0`)

**Missing Dependencies**: If you encounter import errors for `sentence-transformers` or `torch`, these are optional RAG dependencies not in requirements.txt. Install them only if needed for embedding functionality.

### API Endpoint Standards

- Pattern: `/api/{module}/{action}`
- Methods: `GET` (read), `POST` (create/action), `DELETE` (delete)
- Response format: `{"status": "success", "data": {...}}` or `{"error": "message"}`
- Status codes: 200 (success), 400 (validation), 404 (not found), 500 (server error)

### Frontend Code Standards

**Module Separation** (already established in codebase):
- `apiService.js` - HTTP calls to backend
- `chatManager.js` - Chat business logic
- `uiManager.js` - DOM manipulation
- `auth.js` - Authentication flows
- `config.js` - Constants, API endpoints, DOM selectors

When modifying frontend, respect these boundaries - don't mix API calls into UI code or vice versa.

### Language Usage

- **User-facing text**: Vietnamese (error messages, UI labels, chatbot responses)
- **Code/comments**: English or Vietnamese (be consistent within a file)
- **Technical docs**: English
- **API responses**: Vietnamese content for PTIT domain

### Security Rules

- **Never commit**: `.env` files, API keys, passwords
- **Always use**: Environment variables for secrets (`OPENAI_API_KEY`)
- **Always validate**: User inputs in controllers before passing to services
- **Database access**: Use SQLAlchemy ORM only (no raw SQL to prevent injection)

## Common Issues & Troubleshooting

### "ModuleNotFoundError: No module named 'sentence_transformers'"
The embedding library is not in requirements.txt. Install if needed:
```bash
pip install sentence-transformers torch
```

### "OpenAI API authentication failed"
Check your `.env` file:
```bash
# Must have valid API key
OPENAI_API_KEY=sk-proj-...

# Restart server after changing .env
python -m uvicorn BE.main:app --reload --port 8000
```

### "Database is locked" (SQLite)
SQLite doesn't handle concurrent writes well:
```bash
# Kill all Python processes
pkill -f python

# Delete and recreate database
rm chatbot.db
python -m uvicorn BE.main:app --reload --port 8000
```

For production, switch to MySQL by setting `USE_SQLITE=false` in `.env`.

### CORS errors in frontend
Ensure backend CORS settings match your frontend port. Check [BE/core/config.py](BE/core/config.py):
```python
CORS_ORIGINS = [
    "http://127.0.0.1:5500",  # VSCode Live Server
    "http://127.0.0.1:8080",  # Python HTTP Server
    "http://127.0.0.1:3000"
]
```

### RAG returns empty results
Common causes:
1. **No documents ingested** - Use `POST /api/rag/ingest` to add documents first
2. **Embedding model not loaded** - Check console for model loading errors
3. **Similarity threshold too high** - Lower `similarity_threshold` in [rag_config.py](Chatbot/config/rag_config.py)

### Import errors when running BE/main.py
Ensure you're running from project root:
```bash
# Wrong (from BE/ directory)
cd BE && python main.py  # ❌

# Correct (from root directory)
python -m uvicorn BE.main:app --reload  # ✅
```

### DataManagment service won't start
The Flask service needs its own dependencies:
```bash
pip install flask flask-cors python-docx
python DataManagment/main.py
```

## Quick Reference

### Essential Files
- [BE/main.py](BE/main.py) - Main FastAPI application entry point
- [BE/core/config.py](BE/core/config.py) - Database and CORS configuration
- [Chatbot/config/rag_config.py](Chatbot/config/rag_config.py) - RAG system configuration
- [Chatbot/controllers/RAGController.py](Chatbot/controllers/RAGController.py) - All RAG logic
- [requirements.txt](requirements.txt) - Python dependencies
- [.env.example](.env.example) - Environment variable template

### Key Ports
- `8000` - Backend + RAG (FastAPI)
- `5000` - DataManagment (Flask)
- `8080` - Frontend (Python HTTP server)
- `5500` - Frontend (VSCode Live Server)

### Database File
- `./chatbot.db` - SQLite database (auto-created, git-ignored)
