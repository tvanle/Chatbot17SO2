# RAG Module - Chatbot17SO2

Hệ thống RAG (Retrieval-Augmented Generation) cho chatbot tư vấn thông tin PTIT.

## Kiến trúc

Dự án được xây dựng theo kiến trúc 3 lớp MVC với DAO pattern, tuân thủ theo PlantUML diagrams trong `kichban.txt`:

```
Chatbot/
├── models/              # Database models (Document, Chunk, Embedding)
├── dao/                 # Data Access Objects (DocumentDAO, ChunkDAO, VectorIndexDAO)
├── services/            # Business logic
│   ├── VectorizerService.py      # Text → Vector embedding
│   ├── RetrieverService.py       # Vector search + hydration
│   ├── GeneratorService.py       # LLM-based answer generation
│   └── ModelClient.py            # LLM API client
├── controllers/         # FastAPI endpoints
│   └── RAGController.py          # /api/rag/answer, /api/rag/ingest
├── entities/            # DTOs/Request-Response models
├── utils/               # Utilities (chunker, token counter)
└── config/              # Configuration
```

## Database Schema (ERD)

```
documents (1) ──→ (*) chunks (1) ──→ (1) embeddings
```

- **documents**: Tài liệu nguồn (PDF, web pages, etc.)
- **chunks**: Các đoạn văn bản nhỏ được split từ document
- **embeddings**: Vector representations của chunks (1-to-1)

## API Endpoints

### 1. POST `/api/rag/ingest` - Nhập tài liệu

Upload và index một tài liệu mới vào hệ thống.

**Request:**
```json
{
  "namespace_id": "ptit_docs",
  "document_title": "Quy chế đào tạo 2024",
  "content": "Điều 1. Phạm vi và đối tượng áp dụng..."
}
```

**Response:**
```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_count": 42
}
```

**Flow:**
1. Lưu document vào DB
2. Split content thành chunks
3. Tạo embeddings cho từng chunk
4. Lưu embeddings vào vector index

### 2. POST `/api/rag/answer` - Trả lời câu hỏi

Truy vấn chatbot với câu hỏi, nhận câu trả lời có trích dẫn.

**Request:**
```json
{
  "namespace_id": "ptit_docs",
  "question": "Điều kiện tốt nghiệp của sinh viên PTIT là gì?",
  "top_k": 5,
  "token_budget": 2000
}
```

**Response:**
```json
{
  "answer": "Sinh viên PTIT phải hoàn thành đủ số tín chỉ theo chương trình...",
  "citations": [
    {
      "chunk_id": "abc123",
      "score": 0.89,
      "chunk": {
        "text": "Điều kiện tốt nghiệp...",
        "tokens": 45
      },
      "doc": {
        "title": "Quy chế đào tạo 2024",
        "source_uri": "https://..."
      }
    }
  ]
}
```

**Flow:**
1. Vectorize question
2. Search vector index → top-K chunks
3. Hydrate chunks + documents từ DB
4. Fit contexts within token budget
5. Generate answer với LLM
6. Return answer + citations

### 3. GET `/api/rag/documents` - Liệt kê tài liệu

**Query params:** `limit`, `offset`

### 4. GET `/api/rag/documents/{doc_id}` - Chi tiết tài liệu

### 5. DELETE `/api/rag/documents/{doc_id}` - Xóa tài liệu

### 6. GET `/api/rag/health` - Health check

## Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

**Core dependencies:**
- `sentence-transformers` - Embedding model
- `torch` - PyTorch backend
- `numpy` - Vector operations
- `openai` / `anthropic` - LLM APIs (optional)

### 2. Cấu hình

Tạo file `.env` hoặc set environment variables:

```bash
# LLM API Keys (chọn 1 trong 2)
OPENAI_API_KEY=sk-...
# hoặc
ANTHROPIC_API_KEY=sk-ant-...

# Database (đã có sẵn trong BE/core/config.py)
# Không cần config thêm nếu dùng SQLite
```

### 3. Chạy server

```bash
python -m uvicorn BE.main:app --reload --port 8000
```

Server khởi động tại `http://127.0.0.1:8000`

- Swagger UI: http://127.0.0.1:8000/docs
- RAG Health: http://127.0.0.1:8000/api/rag/health

### 4. Test API

**Ingest một tài liệu:**
```bash
curl -X POST http://127.0.0.1:8000/api/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "namespace_id": "ptit_docs",
    "document_title": "Test Document",
    "content": "PTIT là Học viện Công nghệ Bưu chính Viễn thông..."
  }'
```

**Hỏi câu hỏi:**
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

File: `Chatbot/config/rag_config.py`

**Embedding models:**
- `sentence-transformers/all-MiniLM-L6-v2` (mặc định, 384 dim)
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingual)
- `BAAI/bge-small-en-v1.5` (SOTA)

**LLM backends:**
- `openai`: GPT-3.5-turbo, GPT-4, GPT-4-turbo
- `anthropic`: Claude 3 (Sonnet, Opus)
- `local`: Local models (placeholder)

**Chunking settings:**
- `chunk_size`: 512 characters
- `chunk_overlap`: 50 characters
- `chunk_separator`: `\n\n` (paragraphs)

**Retrieval settings:**
- `top_k`: 5 chunks
- `token_budget`: 2000 tokens
- `similarity_threshold`: 0.5

## Advanced Usage

### Custom Embedding Model

```python
from Chatbot.services.VectorizerService import VectorizerService

vectorizer = VectorizerService(
    embed_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
vector = vectorizer.embed("Xin chào PTIT")
```

### Custom LLM

```python
from Chatbot.services.ModelClient import ModelClient

client = ModelClient(
    model_name="gpt-4",
    backend="openai",
    api_key="sk-..."
)
answer = client.complete("What is PTIT?", max_tokens=200)
```

### Enable FAISS (faster search)

1. Uncomment trong `requirements.txt`:
   ```
   faiss-cpu==1.7.4
   ```

2. Update `rag_config.py`:
   ```python
   use_faiss: bool = True
   ```

3. Rebuild index:
   ```python
   from Chatbot.dao.VectorIndexDAO import VectorIndexDAO
   vidx = VectorIndexDAO(db, use_faiss=True)
   vidx._rebuild_faiss_index()
   ```

## Testing

### Unit Tests (TODO)

```bash
pytest Chatbot/tests/
```

### Manual Testing với Swagger UI

1. Mở http://127.0.0.1:8000/docs
2. Test `/api/rag/ingest` để upload tài liệu
3. Test `/api/rag/answer` để hỏi câu hỏi
4. Kiểm tra `citations` trong response

## Troubleshooting

### 1. "sentence-transformers not installed"

```bash
pip install sentence-transformers torch
```

### 2. "OpenAI API key not found"

```bash
export OPENAI_API_KEY=sk-...
# hoặc tạo file .env
```

### 3. Database tables not created

Đảm bảo models được import trong `BE/main.py`:
```python
from Chatbot.models import Document, Chunk, Embedding
```

### 4. Slow vector search

- Enable FAISS: `use_faiss=True` trong config
- Hoặc dùng ChromaDB/Pinecone cho production

## Production Deployment

### Recommendations:

1. **Vector Store**: Dùng Pinecone hoặc Weaviate thay vì database
2. **LLM**: Deploy local model (Llama 3, Mistral) để tiết kiệm chi phí
3. **Caching**: Redis cache cho frequently asked questions
4. **Monitoring**: Log latency, token usage, error rates
5. **Rate Limiting**: Throttle API requests
6. **Authentication**: Add JWT auth cho RAG endpoints

### Example với Pinecone:

```python
# VectorIndexDAO với Pinecone
import pinecone

class VectorIndexDAO:
    def __init__(self, pinecone_api_key, index_name):
        pinecone.init(api_key=pinecone_api_key)
        self.index = pinecone.Index(index_name)

    def query(self, namespace, query_vector, top_k):
        results = self.index.query(
            vector=query_vector.tolist(),
            top_k=top_k,
            namespace=namespace
        )
        return [(match.id, match.score) for match in results.matches]
```

## References

- Kiến trúc theo: `Chatbot/kichban.txt` (4 PlantUML diagrams)
- ERD: Document → Chunks → Embedding (1-to-1)
- Sequence diagrams: Answer flow & Ingest flow
- Class diagram: Controllers → Services → DAO → Models

## Contributing

Để thêm features mới:

1. Update models trong `models/`
2. Update DAO trong `dao/`
3. Update services trong `services/`
4. Add endpoints trong `controllers/RAGController.py`
5. Update tests

## License

MIT License
