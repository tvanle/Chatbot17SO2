from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from BE.core.config import settings
from BE.db.session import Base, engine
from BE.controllers import auth as auth_controller
from BE.controllers import chat as chat_controller
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

# Tạo bảng khi ứng dụng khởi động; ghi log chi tiết và đánh dấu trạng thái DB
@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        app.state.db_ready = True
        logging.info("DB initialization succeeded")
    except Exception:
        app.state.db_ready = False
        logging.exception("DB initialization failed on startup")

@app.get("/health")
def health():
    return {"ok": True, "db_available": getattr(app.state, "db_ready", False)}
