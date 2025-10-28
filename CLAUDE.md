# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Chatbot17SO2** is a RAG-powered chatbot system for PTIT (Hoc vien Cong nghe Buu chinh Vien thong) information consulting. It's a full-stack application with a FastAPI backend, vanilla JavaScript frontend, and a sophisticated RAG (Retrieval-Augmented Generation) system for document-based question answering.

## Architecture

The project follows a **3-tier MVC architecture with DAO pattern**, split into three main modules:

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
Flask-based data management service for document uploads and web crawling.
- **Models**: User, FileData, CrawledData
- **Controllers**: FileDataDAO, CrawledDataDAO, StatisticDAO
- **Features**: File upload (DOCX, TXT), web crawling, statistics

### 4. FE (Frontend)
Vanilla JavaScript SPA with modular architecture.
- **Structure**: `js/main.js`, `js/chatManager.js`, `js/apiService.js`, `js/uiManager.js`, `js/auth.js`
- **Pages**: `index.html` (chat), `login.html` (auth)
- **API Base**: `http://127.0.0.1:8000`

## Common Commands

### Development Setup

```bash
# Install all dependencies (from root)
pip install -r requirements.txt

# OR install per module
pip install -r BE/requirements.txt
pip install -r Chatbot/requirements.txt
pip install -r DataManagement/requirements.txt
```

### Running Services

**Backend (FastAPI - Port 8000)**:
```bash
# From root directory
python -m uvicorn BE.main:app --reload --port 8000

# With hot reload for development
uvicorn BE.main:app --reload --host 127.0.0.1 --port 8000
```

**DataManagement Service (Flask - Port 5000)**:
```bash
# From root directory
python DataManagment/main.py
```

**Frontend**:
```bash
# Serve with Python HTTP server
cd FE && python -m http.server 8080

# Or use VSCode Live Server (port 5500)
# Right-click index.html → "Open with Live Server"
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

### RAG Controller Logic
**Important**: All RAG logic is in [Chatbot/controllers/RAGController.py](Chatbot/controllers/RAGController.py) - there is NO separate RAGService. The controller directly orchestrates VectorizerService, RetrieverService, and GeneratorService.

### Database Schema
- **documents**: Source documents (PDF, web pages, etc.)
- **chunks**: Text segments split from documents (1 document → many chunks)
- **embeddings**: Vector representations (1 chunk → 1 embedding)

All models are SQLAlchemy ORM models registered with `Base.metadata` in [BE/main.py](BE/main.py:11).

### Service Singletons
VectorizerService and GeneratorService are singleton instances in RAGController to avoid reloading heavy ML models on every request.

### Directory Structure Quirk
Note: There are TWO directories:
- `DataManagement/` (correct spelling, newer, only has `requirements.txt`)
- `DataManagment/` (typo, contains actual code: `main.py`, `models/`, `controller/`)

**Use `DataManagment/` (with typo) for actual data management code.**

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

**Core RAG dependencies**:
- `sentence-transformers==2.3.1` - Embedding model
- `torch==2.1.2` - PyTorch backend
- `numpy==1.24.3` - Vector operations
- `openai==1.12.0` - OpenAI LLM API
- `anthropic==0.18.1` - Anthropic LLM API

**Optional (commented out in requirements.txt)**:
- `faiss-cpu` - Fast vector search (enable in `rag_config.py`)
- `chromadb` - Alternative vector store
- `pinecone-client` - Cloud vector store
- `tiktoken` - Better tokenization

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

## Code Style & Design Principles

### Clean Code Standards

**Naming Conventions**:
- Use descriptive, intention-revealing names for variables, functions, and classes
- Python: `snake_case` for functions/variables, `PascalCase` for classes
- JavaScript: `camelCase` for functions/variables, `PascalCase` for classes/components
- Avoid abbreviations unless they are widely understood (e.g., `dao`, `rag`, `api`)

**Function Design**:
- Functions should do ONE thing and do it well (Single Responsibility Principle)
- Keep functions small (ideally < 20 lines)
- Prefer fewer function parameters (max 3-4; use objects/dicts for more)
- Avoid side effects - functions should be predictable

**Code Organization**:
- Follow the existing 3-tier MVC + DAO architecture strictly
- **Controller** → handles HTTP requests/responses only
- **Service** → contains business logic
- **DAO** → database access only
- **Model** → data structures and ORM mappings

**Error Handling**:
- Use specific exception types, not generic `Exception`
- Always include meaningful error messages
- Log errors with context (user_id, request_id, etc.)
- Return appropriate HTTP status codes (400 for validation, 404 for not found, 500 for server errors)

**Comments & Documentation**:
- Write self-documenting code (good names > comments)
- Use docstrings for all public functions/classes (Python) or JSDoc (JavaScript)
- Explain WHY, not WHAT (code shows what, comments explain why)
- Update comments when code changes

### Project-Specific Rules

**File Creation Policy**:
- **NEVER** create documentation files (*.md, README.md, GUIDE.md, etc.) unless explicitly requested by the user
- **NEVER** create shell script files (*.sh, *.bash) for running commands
- **ALWAYS** run commands directly in the terminal using `bash` tool instead of creating script files
- **NEVER** create configuration templates or example files unless explicitly requested

**Command Execution**:
- Use direct bash commands instead of script files
- Example: Run `uvicorn BE.main:app --reload` directly, NOT `./start.sh`
- Chain commands with `&&` when needed: `pip install -r requirements.txt && uvicorn BE.main:app --reload`

**Database Migrations**:
- Use SQLAlchemy's automatic table creation (`Base.metadata.create_all()`)
- DO NOT create Alembic migration files unless explicitly requested
- Schema changes should be made in Model classes, not manual SQL

**Dependencies**:
- Add new dependencies to the appropriate `requirements.txt` file:
  - `BE/requirements.txt` for backend/auth/chat features
  - `Chatbot/requirements.txt` for RAG/ML features
  - `DataManagement/requirements.txt` for data processing features
- Update root `requirements.txt` only when adding project-wide dependencies
- Pin exact versions (e.g., `fastapi==0.120.0`)

**Testing**:
- Write tests only when implementing new features (not for documentation)
- Place tests in appropriate module: `BE/tests/`, `Chatbot/tests/`
- Use pytest for Python tests
- Test files should mirror source structure: `services/chatService.py` → `tests/test_chatService.py`

**Frontend Code**:
- Keep frontend modular: separate API calls (`apiService.js`), UI updates (`uiManager.js`), and business logic (`chatManager.js`)
- Avoid mixing concerns in a single file
- Use ES6+ features (arrow functions, destructuring, async/await)
- Keep DOM queries in `config.js` for reusability

**API Design**:
- Follow existing endpoint patterns: `/api/{module}/{action}`
- Use proper HTTP methods: GET (read), POST (create/action), DELETE (delete)
- Return consistent JSON structure: `{"status": "success", "data": {...}}` or `{"error": "message"}`
- Include proper status codes

**Security**:
- Never commit API keys, passwords, or secrets to git
- Use environment variables for sensitive data
- Validate all user inputs in controllers before passing to services
- Use parameterized queries (SQLAlchemy ORM) to prevent SQL injection

### Vietnamese Language Usage

- All user-facing messages, error messages, and UI text should be in Vietnamese
- Code comments can be in English or Vietnamese (consistency within a file)
- API documentation and technical docs can be in English
- Database content and RAG responses should be in Vietnamese for PTIT use case
