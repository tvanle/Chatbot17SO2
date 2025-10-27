# RAG Architecture - Chatbot17SO2

## Tổng quan

Hệ thống RAG (Retrieval-Augmented Generation) được thiết kế theo kiến trúc **3 lớp MVC với DAO pattern**, tuân thủ 100% theo kịch bản trong `kichban.txt`.

## Sơ đồ kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│                        (BE/main.py)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        ┌───────▼────────┐      ┌──────▼──────┐
        │ Auth/Chat      │      │ RAG Module  │
        │ Controllers    │      │ Controller  │
        └────────────────┘      └──────┬──────┘
                                       │
                            ┌──────────┴──────────┐
                            │                     │
                    ┌───────▼────────┐   ┌────────▼─────────┐
                    │   Services     │   │    Entities      │
                    │ (Business      │   │    (DTOs)        │
                    │  Logic)        │   │                  │
                    └───────┬────────┘   └──────────────────┘
                            │
                    ┌───────┴────────┐
                    │                │
            ┌───────▼───────┐ ┌─────▼──────┐
            │     DAO        │ │   Models   │
            │ (Data Access)  │ │ (Database) │
            └───────┬────────┘ └─────┬──────┘
                    │                │
                    └────────┬───────┘
                             │
                    ┌────────▼─────────┐
                    │    Database      │
                    │  (SQLite/MySQL)  │
                    └──────────────────┘
```

## Cấu trúc thư mục

```
Chatbot/
├── kichban.txt                    # Kịch bản thiết kế (4 PlantUML diagrams)
├── README.md                      # Hướng dẫn sử dụng
├── ARCHITECTURE.md                # Tài liệu kiến trúc (file này)
│
├── models/                        # SQLAlchemy ORM Models
│   ├── Document.py               #   - documents table
│   ├── Chunk.py                  #   - chunks table
│   └── Embedding.py              #   - embeddings table
│
├── dao/                          # Data Access Objects
│   ├── DocumentDAO.py            #   - CRUD cho documents
│   ├── ChunkDAO.py               #   - CRUD cho chunks
│   └── VectorIndexDAO.py         #   - Vector similarity search
│
├── services/                     # Business Logic Layer
│   ├── VectorizerService.py     #   - Text → Vector (sentence-transformers)
│   ├── RetrieverService.py      #   - Vector search + hydration
│   ├── GeneratorService.py      #   - LLM answer generation
│   └── ModelClient.py            #   - LLM API wrapper (OpenAI/Anthropic)
│
├── controllers/                  # FastAPI Endpoints
│   └── RAGController.py          #   - /api/rag/answer, /api/rag/ingest
│
├── entities/                     # Request/Response DTOs
│   ├── AnswerRequest.py
│   ├── AnswerResult.py
│   ├── IngestRequest.py
│   ├── IngestResult.py
│   └── RetrievalHit.py
│
├── utils/                        # Utility Functions
│   ├── chunker.py                #   - Text splitting logic
│   └── token_counter.py          #   - Token estimation
│
└── config/                       # Configuration
    └── rag_config.py             #   - RAG settings (models, params)
```

## Database Schema (ERD)

Theo PlantUML ERD trong `kichban.txt`:

```sql
-- documents: Tài liệu nguồn
CREATE TABLE documents (
    id VARCHAR(36) PRIMARY KEY,
    source_uri VARCHAR(512),
    title VARCHAR(255),
    text TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- chunks: Đoạn văn bản nhỏ từ document
CREATE TABLE chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE CASCADE,
    idx INTEGER,           -- Chunk index trong document
    text TEXT,
    tokens INTEGER,        -- Token count
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- embeddings: Vector representations (1-to-1 với chunk)
CREATE TABLE embeddings (
    id VARCHAR(36) PRIMARY KEY,
    chunk_id VARCHAR(36) UNIQUE REFERENCES chunks(id) ON DELETE CASCADE,
    model_name VARCHAR(128),
    dim INTEGER,
    vector_blob BLOB,      -- Serialized numpy array
    created_at TIMESTAMP
);
```

**Relationships:**
- `1 document` → `N chunks` (1-to-many)
- `1 chunk` → `1 embedding` (1-to-1)

## Class Diagram

Theo PlantUML Class Diagram trong `kichban.txt`:

### Controllers Layer
```python
RAGController
├── answer(AnswerRequest) → AnswerResult
└── ingest(IngestRequest) → IngestResult
```

### Services Layer
```python
VectorizerService
├── embed(text) → vector
└── embed_batch(texts) → vectors

RetrieverService
├── search(namespace, qvec, topK) → List[RetrievalHit]
└── (uses VectorIndexDAO, ChunkDAO, DocumentDAO)

GeneratorService
├── generate(question, contexts) → answer
└── (uses ModelClient)

ModelClient
└── complete(prompt, maxTokens) → text
```

### DAO Layer
```python
DocumentDAO
├── find_by_id(id) → Document
├── upsert(doc) → doc_id
├── find_all() → List[Document]
└── delete(id) → bool

ChunkDAO
├── find_by_ids(ids) → List[Chunk]
├── insert(chunk) → chunk_id
├── insert_batch(chunks) → List[chunk_id]
└── find_by_document(doc_id) → List[Chunk]

VectorIndexDAO
├── query(namespace, qvec, topK) → List[(chunk_id, score)]
└── upsert(namespace, pairs) → void
```

## Sequence Diagrams

### 1. Answer Flow (POST /api/rag/answer)

Theo Sequence Diagram trong `kichban.txt`:

```
User → RAGController: answer(AnswerRequest)
│
├─→ VectorizerService: embed(question)
│   └─→ qvec
│
├─→ RetrieverService: search(namespace, qvec, topK)
│   │
│   ├─→ VectorIndexDAO: query(namespace, qvec, topK)
│   │   └─→ [(chunk_id, score)]
│   │
│   ├─→ ChunkDAO: find_by_ids([chunk_id...])
│   │   └─→ List[Chunk]
│   │
│   ├─→ DocumentDAO: find_by_id(doc_id) [per doc]
│   │   └─→ Document
│   │
│   └─→ List[RetrievalHit{chunk, doc, score}]
│
├─→ takeWithinBudget(hits, token_budget)
│   └─→ contexts
│
├─→ GeneratorService: generate(question, contexts)
│   │
│   └─→ ModelClient: complete(prompt, maxTokens)
│       └─→ answer
│
└─→ AnswerResult{answer, citations}
```

**Steps:**
1. Vectorize câu hỏi
2. Search vector index → top-K chunk IDs + scores
3. Hydrate chunks từ DB
4. Hydrate documents từ DB
5. Fit contexts trong token budget
6. Generate answer bằng LLM
7. Return answer với citations

### 2. Ingest Flow (POST /api/rag/ingest)

Theo Sequence Diagram trong `kichban.txt`:

```
Admin → RAGController: ingest(IngestRequest)
│
├─→ DocumentDAO: upsert(Document)
│   └─→ doc_id
│
├─→ Chunker: split(content)
│   └─→ chunks: List[Chunk]
│
├─→ ChunkDAO: insert_batch(chunks)
│   └─→ [chunk_id...]
│
├─→ VectorizerService: embed_batch([chunk.text])
│   └─→ vectors: List[float[]]
│
├─→ VectorIndexDAO: upsert(namespace, [(chunk_id, vector)...])
│   └─→ ok
│
└─→ IngestResult{doc_id, chunk_count}
```

**Steps:**
1. Upsert document vào DB
2. Split content thành chunks
3. Insert chunks vào DB
4. Embed tất cả chunks (batch)
5. Upsert vectors vào index
6. Return doc_id và chunk_count

## API Endpoints

### RAG Endpoints (`/api/rag/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/answer` | Trả lời câu hỏi với RAG |
| POST | `/api/rag/ingest` | Upload và index tài liệu |
| GET | `/api/rag/documents` | Liệt kê tài liệu |
| GET | `/api/rag/documents/{id}` | Chi tiết tài liệu |
| DELETE | `/api/rag/documents/{id}` | Xóa tài liệu |
| GET | `/api/rag/health` | Health check |

### Existing Endpoints (`/api/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Đăng nhập |
| POST | `/api/auth/register` | Đăng ký |
| POST | `/api/auth/logout` | Đăng xuất |
| GET | `/api/auth/profile` | Thông tin user |
| ... | `/api/chat/*` | Chat endpoints |

## Technology Stack

### Backend Core
- **FastAPI 0.120.0** - Web framework
- **Uvicorn 0.38.0** - ASGI server
- **SQLAlchemy 2.0.44** - ORM
- **Pydantic 2.5.3** - Data validation

### RAG Core
- **sentence-transformers 2.3.1** - Embedding models
- **PyTorch 2.1.2** - Deep learning backend
- **NumPy 1.24.3** - Vector operations

### LLM Integration (Optional)
- **openai 1.12.0** - OpenAI GPT API
- **anthropic 0.18.1** - Anthropic Claude API

### Vector Stores (Optional)
- **faiss-cpu** - Fast similarity search (in-memory)
- **chromadb** - Vector database
- **pinecone-client** - Managed vector DB

### Database
- **SQLite** (default) - Embedded database
- **MySQL** (optional) - Production database

## Configuration

File: `Chatbot/config/rag_config.py`

```python
class RAGConfig:
    # Embedding
    embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension = 384

    # LLM
    llm_backend = "openai"  # "openai" | "anthropic" | "local"
    llm_model = "gpt-3.5-turbo"
    llm_max_tokens = 512
    llm_temperature = 0.7

    # Vector Store
    vector_store_type = "database"  # "database" | "faiss" | "chromadb"
    use_faiss = False

    # Chunking
    chunk_size = 512
    chunk_overlap = 50

    # Retrieval
    default_top_k = 5
    default_token_budget = 2000
    similarity_threshold = 0.5
```

## Data Flow

### Ingest Pipeline
```
Document (PDF/Text/Web)
    ↓
Split into Chunks (chunker.py)
    ↓
Generate Embeddings (VectorizerService)
    ↓
Store in Database (DocumentDAO, ChunkDAO)
    ↓
Index Vectors (VectorIndexDAO)
```

### Query Pipeline
```
User Question
    ↓
Generate Query Embedding (VectorizerService)
    ↓
Vector Similarity Search (VectorIndexDAO)
    ↓
Retrieve Top-K Chunks (RetrieverService)
    ↓
Hydrate Chunks + Documents (DAO Layer)
    ↓
Fit within Token Budget (token_counter.py)
    ↓
Generate Answer (GeneratorService + LLM)
    ↓
Return Answer + Citations
```

## Design Patterns

### 1. DAO Pattern
- **DocumentDAO**, **ChunkDAO**, **VectorIndexDAO**
- Tách biệt logic truy xuất database khỏi business logic
- Dễ test và mock

### 2. Service Layer Pattern
- **VectorizerService**, **RetrieverService**, **GeneratorService**
- Encapsulate business logic
- Reusable components

### 3. DTO Pattern
- **AnswerRequest**, **AnswerResult**, **IngestRequest**, **IngestResult**
- Type-safe request/response với Pydantic validation

### 4. Dependency Injection
- FastAPI `Depends(get_db)` cho database sessions
- Services được inject vào controllers

### 5. Repository Pattern
- VectorIndexDAO abstraction cho nhiều vector stores
- Dễ swap giữa database, FAISS, ChromaDB, Pinecone

## Performance Considerations

### Vector Search
- **Database mode**: O(n) linear scan, slow cho >10k documents
- **FAISS mode**: O(log n) với index, fast cho >100k documents
- **Production**: Dùng Pinecone/Weaviate cho scale lớn

### Embedding Generation
- **Batch processing**: embed_batch() nhanh hơn embed() đơn lẻ
- **Model size**: MiniLM (384 dim) vs MPNet (768 dim) trade-off
- **GPU**: Dùng GPU để tăng tốc (set device='cuda')

### Token Budget
- Limit context size để tránh vượt quá LLM context window
- Default 2000 tokens ≈ 8000 characters
- GPT-3.5-turbo: 4k context, GPT-4-turbo: 128k context

## Testing Strategy

### Unit Tests
- Test DAO methods với mock database
- Test chunker với known inputs
- Test token counter accuracy

### Integration Tests
- Test full ingest pipeline
- Test full answer pipeline
- Test API endpoints

### Load Tests
- Benchmark vector search latency
- Test concurrent requests
- Measure token usage

## Future Enhancements

### 1. Advanced Retrieval
- [ ] Cross-encoder re-ranking
- [ ] Hybrid search (BM25 + vector)
- [ ] Multi-query retrieval

### 2. Better Chunking
- [ ] Semantic chunking (split by topics)
- [ ] Vietnamese NLP (underthesea, vncorenlp)
- [ ] Table/image extraction

### 3. Production Features
- [ ] Async processing với Celery
- [ ] Redis caching
- [ ] Rate limiting
- [ ] API authentication (JWT)
- [ ] Logging và monitoring

### 4. UI Integration
- [ ] Frontend chat interface
- [ ] Document upload UI
- [ ] Admin dashboard

## References

- **Kịch bản**: `Chatbot/kichban.txt` (4 PlantUML diagrams)
- **README**: `Chatbot/README.md` (Hướng dẫn sử dụng)
- **Main docs**: Backend trong `BE/`, Frontend trong `FE/`

## Developers

- Architecture design: Theo kịch bản PlantUML
- Implementation: MVC + DAO pattern
- Framework: FastAPI + SQLAlchemy + Sentence Transformers
