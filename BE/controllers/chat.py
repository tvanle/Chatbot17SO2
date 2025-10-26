from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from BE.db.session import get_db
from BE.services.chatService import ChatService

# Controller: Tầng giao tiếp với FE, xử lý HTTP requests/responses
router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/create")
def create_chat(
    user_id: int = Form(...),
    title: str = Form(...),
    db: Session = Depends(get_db),
):
    """Tạo chat mới"""
    result = ChatService.create_chat(db, user_id, title)
    return JSONResponse(content=result, status_code=200)

@router.get("/list")
def get_chat_list(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Lấy danh sách chat của user"""
    result = ChatService.get_chat_list(db, user_id)
    return JSONResponse(content=result, status_code=200)

@router.get("/messages")
def get_chat_messages(
    chat_id: int,
    db: Session = Depends(get_db),
):
    """Lấy tất cả messages của 1 chat"""
    result = ChatService.get_chat_messages(db, chat_id)
    return JSONResponse(content=result, status_code=200)

@router.post("/send")
def send_message(
    chat_id: int = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    """Gửi message và nhận response từ bot"""
    result = ChatService.send_message(db, chat_id, content)
    return JSONResponse(content=result, status_code=200)

@router.get("/models")
def get_models():
    """Lấy danh sách models có thể sử dụng"""
    result = ChatService.get_models()
    return JSONResponse(content=result, status_code=200)
