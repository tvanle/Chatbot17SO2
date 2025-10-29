"""
Chatbot RAG Server - Standalone FastAPI application for RAG system

Chạy server này độc lập với BE server:
    python -m uvicorn Chatbot.main:app --reload --port 8001

API Endpoints:
    POST /api/rag/answer      - Trả lời câu hỏi với RAG
    POST /api/rag/ingest      - Nạp document vào vector store
    GET  /api/rag/documents   - Liệt kê documents
    GET  /api/rag/health      - Health check
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Chatbot.controllers.RAGController import router as rag_router
from BE.db.session import Base, engine
from dotenv import load_dotenv
import logging

# Load environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
load_dotenv()

# Import models để register với Base.metadata
from Chatbot.models import Document, Chunk, Embedding

# Tạo FastAPI app cho Chatbot
app = FastAPI(
    title="Chatbot RAG API",
    description="RAG (Retrieval-Augmented Generation) system cho PTIT chatbot",
    version="1.0.0"
)

# CORS configuration - cho phép BE server và frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",      # BE server
        "http://localhost:8000",       # BE server (localhost)
        "http://127.0.0.1:5500",      # VSCode Live Server
        "http://127.0.0.1:3000",      # Alternative frontend
        "http://127.0.0.1:8080",      # Python HTTP server
        "null"                         # File protocol
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register RAG router
app.include_router(rag_router)

# Database initialization
@app.on_event("startup")
def startup():
    """
    Tạo bảng database khi khởi động
    Tự động tạo: documents, chunks, embeddings
    """
    try:
        Base.metadata.create_all(bind=engine)
        app.state.db_ready = True
        logging.info("✅ Chatbot RAG database initialized successfully")
        logging.info("📊 Tables: documents, chunks, embeddings")
    except Exception as e:
        app.state.db_ready = False
        logging.exception(f"❌ Chatbot RAG database initialization failed: {e}")

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "Chatbot RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/rag/health"
    }

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "ok": True,
        "service": "Chatbot RAG Server",
        "db_available": getattr(app.state, "db_ready", False)
    }
