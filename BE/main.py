from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from BE.core.config import settings
from BE.db.session import Base, engine
from BE.controllers import auth as auth_controller
from BE.controllers import chat as chat_controller
from Chatbot.controllers import RAGController
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Chatbot17 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_controller.router)
app.include_router(chat_controller.router)
app.include_router(RAGController.router)

# Tạo bảng khi ứng dụng khởi động; ghi log chi tiết và đánh dấu trạng thái DB
@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        app.state.db_ready = True
        logging.info("✅ DB initialization succeeded")
    except Exception:
        app.state.db_ready = False
        logging.exception("❌ DB initialization failed on startup")

    # CRITICAL: Pre-load embedding model at startup and STORE IN app.state
    # This ensures the model is loaded once and reused for all requests
    # Using app.state instead of module globals to survive uvicorn reloads
    try:
        logging.info("🔄 Pre-loading RAG services at startup...")
        print("🔄 Pre-loading RAG services at startup...")

        from Chatbot.services.VectorizerService import VectorizerService
        from Chatbot.services.GeneratorService import GeneratorService

        # Create and store in app.state (NOT module globals)
        app.state.vectorizer = VectorizerService()
        app.state.generator = GeneratorService()

        logging.info(f"✅ VectorizerService loaded: model={app.state.vectorizer.model is not None}")
        logging.info(f"✅ GeneratorService loaded")
        print(f"✅ VectorizerService loaded: model={app.state.vectorizer.model is not None}")
        print(f"✅ GeneratorService loaded")

        app.state.rag_ready = True
    except Exception as e:
        app.state.rag_ready = False
        app.state.vectorizer = None
        app.state.generator = None
        logging.exception(f"❌ RAG services initialization failed: {e}")
        print(f"❌ RAG services initialization failed: {e}")
        import traceback
        traceback.print_exc()

@app.get("/health")
def health():
    return {"ok": True, "db_available": getattr(app.state, "db_ready", False)}
