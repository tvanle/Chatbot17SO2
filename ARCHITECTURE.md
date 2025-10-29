# Kiến trúc Project - Chatbot PTIT

## Tổng quan Architecture

Project sử dụng **Microservice Architecture** với 2 service chính:

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND (FE/)                    │
│              HTML/CSS/JavaScript ES6                │
│                 http://localhost:3000               │
└─────────────────────────────────────────────────────┘
                         │ HTTP
                         ↓
┌─────────────────────────────────────────────────────┐
│              BACKEND SERVICE (BE/)                  │
│            FastAPI - Port 8000                      │
│  ┌──────────────────────────────────────────────┐  │
│  │ Controllers (HTTP Endpoints)                 │  │
│  │  - AuthController: /api/auth/*               │  │
│  │  - ChatController: /api/chat/*               │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ Services (Business Logic)                    │  │
│  │  - AuthService: Xử lý login/register        │  │
│  │  - ChatService: Quản lý chat persistence    │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ DAO (Data Access Object)                     │  │
│  │  - UserDAO: CRUD User                        │  │
│  │  - ChatDAO: CRUD Chat                        │  │
│  │  - MessageDAO: CRUD Message                  │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ Database: SQLite (chatbot.db)                │  │
│  │  - tblUser                                    │  │
│  │  - tblChat                                    │  │
│  │  - tblMessage                                 │  │
│  │  - tblModel                                   │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         │ HTTP (Internal)
                         ↓
┌─────────────────────────────────────────────────────┐
│           CHATBOT/RAG SERVICE (Chatbot/)            │
│              FastAPI - Port 8000                    │
│  ┌──────────────────────────────────────────────┐  │
│  │ RAGController: /api/rag/*                    │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ Services:                                    │  │
│  │  - ModelClient: OpenAI API Client           │  │
│  │  - GeneratorService: LLM Generation         │  │
│  │  - RetrieverService: Vector Search          │  │
│  │  - VectorizerService: Text Embedding        │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ Database (Shared với BE):                   │  │
│  │  - tblDocument: Documents                    │  │
│  │  - tblChunk: Text chunks                     │  │
│  │  - tblEmbedding: Vector embeddings           │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                         │ HTTPS
                         ↓
┌─────────────────────────────────────────────────────┐
│          🌐 EXTERNAL AI SERVER                      │
│           OpenAI API (GPT-3.5/GPT-4)                │
│        https://api.openai.com/v1/chat/completions   │
└─────────────────────────────────────────────────────┘
```

## Cấu trúc thư mục

```
Chatbot17SO2/
├── .env                          # Environment variables (API keys)
├── .env.example                  # Template cho .env
├── requirements.txt              # Dependencies cho BE
├── ARCHITECTURE.md               # File này
│
├── BE/                           # Backend Service
│   ├── controllers/              # HTTP Controllers (tầng FE communication)
│   │   ├── auth.py              # /api/auth/* endpoints
│   │   └── chat.py              # /api/chat/* endpoints
│   ├── services/                # Business Logic
│   │   ├── authService.py       # Login, Register
│   │   └── chatService.py       # Chat persistence + gọi RAG service
│   ├── dao/                     # Data Access Object (tầng Database)
│   │   ├── UserDAO.py
│   │   ├── ChatDAO.py
│   │   └── MessageDAO.py
│   ├── models/                  # SQLAlchemy Models
│   │   ├── User.py
│   │   ├── Chat.py
│   │   └── Message.py
│   ├── core/
│   │   └── config.py            # Database config
│   ├── db/
│   │   └── session.py           # Database session
│   └── main.py                  # FastAPI app entry point
│
├── Chatbot/                     # RAG/AI Service
│   ├── requirements.txt         # Dependencies riêng cho Chatbot
│   ├── controllers/
│   │   └── RAGController.py     # /api/rag/* endpoints
│   ├── services/
│   │   ├── ModelClient.py       # 🔥 OpenAI API Client
│   │   ├── GeneratorService.py  # LLM Generation với OpenAI
│   │   ├── RetrieverService.py  # Vector search
│   │   └── VectorizerService.py # Text embedding
│   ├── dao/                     # Vector database access
│   ├── models/                  # Document, Chunk, Embedding models
│   └── config/
│       └── rag_config.py        # RAG configuration
│
├── FE/                          # Frontend
│   ├── index.html               # Main chat interface
│   ├── login.html               # Login/Register page
│   ├── css/
│   │   └── style.css
│   └── js/                      # ES6 Modules
│       ├── main.js              # Entry point
│       ├── config.js            # API config, DOM refs
│       ├── utils.js             # Utility functions
│       ├── apiService.js        # HTTP client
│       ├── chatManager.js       # Chat logic
│       ├── uiManager.js         # UI logic
│       └── auth.js              # Auth logic
│
└── docs/                        # Documentation
    ├── class-diagram-detailed.md
    └── sequence-diagram-detailed.md
```

## Luồng xử lý Message

```
1. User nhập message trong FE
   ↓
2. ChatManager.sendMessage() → ApiService.sendMessage()
   ↓
3. POST http://127.0.0.1:8000/api/chat/send
   ↓
4. BE/ChatController.send_message()
   ↓
5. BE/ChatService.send_message():
   - Lưu user message vào DB (MessageDAO.create)
   - 🔥 Gọi RAG service: POST /api/rag/answer
   ↓
6. Chatbot/RAGController.answer_question():
   - RetrieverService: Tìm kiếm vector
   - GeneratorService: Gọi OpenAI API
   ↓
7. Chatbot/ModelClient.complete():
   - 🌐 HTTPS POST → https://api.openai.com/v1/chat/completions
   - Nhận response từ GPT
   ↓
8. Trả response về BE/ChatService
   ↓
9. BE/ChatService:
   - Lưu bot message vào DB
   - Return JSON response
   ↓
10. FE hiển thị bot message
```

## Dependencies

### BE (Backend) - `requirements.txt`
```
fastapi==0.120.0          # Web framework
uvicorn==0.38.0           # ASGI server
sqlalchemy==2.0.44        # ORM
pymysql==1.1.2            # MySQL driver
cryptography==46.0.3      # Security
python-dotenv==1.2.1      # Environment variables
requests==2.31.0          # HTTP client (gọi Chatbot service)
```

### Chatbot (RAG) - `Chatbot/requirements.txt`
```
openai==2.6.1             # 🔥 OpenAI API client
numpy==1.24.3             # Vector operations
sentence-transformers     # Text embedding
torch                     # ML framework
fastapi==0.120.0          # Web framework
sqlalchemy==2.0.44        # Database
```

## Environment Variables (`.env`)

```bash
# OpenAI API Key (BẮT BUỘC)
OPENAI_API_KEY=sk-proj-xxx...

# Database
USE_SQLITE=true
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=
DB_NAME=chatbot_db

# Service URLs
CHATBOT_SERVICE_URL=http://127.0.0.1:8000

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

## Cách chạy Project

### 1. Cài đặt dependencies

```bash
# Backend
pip install -r requirements.txt

# Chatbot/RAG (nếu chạy riêng service)
pip install -r Chatbot/requirements.txt
```

### 2. Cấu hình .env

```bash
cp .env.example .env
# Edit .env và thêm OPENAI_API_KEY
```

### 3. Chạy Backend

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run server
python -m uvicorn BE.main:app --reload --port 8000
```

### 4. Chạy Frontend

```bash
cd FE
python -m http.server 3000
```

### 5. Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs

## API Endpoints

### Auth Service (`/api/auth`)
- `POST /api/auth/register` - Đăng ký
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/logout` - Đăng xuất
- `GET /api/auth/profile` - Lấy profile

### Chat Service (`/api/chat`)
- `POST /api/chat/create` - Tạo chat mới
- `GET /api/chat/list` - Lấy danh sách chat
- `GET /api/chat/messages` - Lấy messages của chat
- `POST /api/chat/send` - Gửi message (gọi RAG)
- `GET /api/chat/models` - Lấy danh sách models

### RAG Service (`/api/rag`)
- `POST /api/rag/answer` - Trả lời câu hỏi với RAG
- `POST /api/rag/ingest` - Ingest documents vào vector DB

## Database Schema

### tblUser
```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
name        VARCHAR(255)
email       VARCHAR(255) UNIQUE
password    VARCHAR(255)
created_at  DATETIME
```

### tblChat
```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
user_id     INTEGER FOREIGN KEY
title       VARCHAR(500)
created_at  DATETIME
updated_at  DATETIME
```

### tblMessage
```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
chat_id     INTEGER FOREIGN KEY
type        ENUM('user', 'assistant')
content     TEXT
model_id    INTEGER FOREIGN KEY (nullable)
created_at  DATETIME
```

### tblModel
```sql
id              INTEGER PRIMARY KEY AUTOINCREMENT
name            VARCHAR(255)
description     TEXT
api_identifier  VARCHAR(255)
is_active       BOOLEAN
```

## Tích hợp OpenAI

**File quan trọng**: `Chatbot/services/ModelClient.py`

```python
from openai import OpenAI
import os

class ModelClient:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def complete(self, prompt: str):
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
```

**Cách hoạt động**:
1. BE/ChatService nhận message từ user
2. Gọi RAG service: `POST /api/rag/answer`
3. RAG/GeneratorService build prompt với context
4. ModelClient gọi OpenAI API qua HTTPS
5. Nhận response từ GPT-3.5/GPT-4
6. Trả về BE và lưu vào database
7. Trả về FE để hiển thị

## Troubleshooting

### Lỗi "ModuleNotFoundError: No module named 'numpy'"
```bash
pip install -r Chatbot/requirements.txt
```

### Lỗi "Authentication failed" với OpenAI
```bash
# Kiểm tra .env
OPENAI_API_KEY=sk-proj-xxx...  # Phải đúng API key
```

### Database locked
```bash
# Kill tất cả processes đang dùng DB
rm chatbot.db
# Restart server để tạo lại DB
```

## Security Notes

⚠️ **QUAN TRỌNG**:
- File `.env` đã được add vào `.gitignore`
- **KHÔNG BAO GIỜ** commit `.env` lên git
- Sử dụng `.env.example` làm template
- API key phải được bảo mật ở server-side

## Contact

- Project Lead: [Tên bạn]
- Email: [Email]
- GitHub: [Link repo]
