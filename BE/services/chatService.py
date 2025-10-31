from sqlalchemy.orm import Session
from BE.dao.ChatDAO import ChatDAO
from BE.dao.MessageDAO import MessageDAO
from BE.dao.ModelDAO import ModelDAO
from BE.models.Message import MessageType
import requests
import os

# Chatbot service URL (có thể chạy trên port khác hoặc server khác)
CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://127.0.0.1:8000")


class ChatService:
    @staticmethod
    def create_chat(db: Session, user_id: int, title: str):
        """Tạo chat mới cho user"""
        chat = ChatDAO.create(db, user_id, title)
        return {
            "ok": True,
            "message": "Tạo chat thành công",
            "chat": {
                "id": chat.id,
                "title": chat.title,
                "created_at": chat.created_at.isoformat(),
            },
        }

    @staticmethod
    def get_chat_list(db: Session, user_id: int):
        """Lấy danh sách chat của user"""
        chats = ChatDAO.find_by_user(db, user_id)
        return {
            "ok": True,
            "chats": [
                {
                    "id": chat.id,
                    "title": chat.title,
                    "updated_at": chat.updated_at.isoformat(),
                }
                for chat in chats
            ],
        }

    @staticmethod
    def get_chat_messages(db: Session, chat_id: int):
        """Lấy tất cả messages của 1 chat"""
        chat = ChatDAO.find_by_id(db, chat_id)
        if not chat:
            return {"ok": False, "message": "Chat không tồn tại"}

        messages = MessageDAO.find_by_chat(db, chat_id)
        return {
            "ok": True,
            "chat": {
                "id": chat.id,
                "title": chat.title,
            },
            "messages": [
                {
                    "id": msg.id,
                    "type": msg.type.value,
                    "content": msg.content,
                    "model_id": msg.model_id,
                    "model_name": msg.model.name if msg.model else None,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
        }

    @staticmethod
    def send_message(db: Session, chat_id: int, content: str, model_name: str = None):
        """
        Gửi message của user và trả về response của bot với RAG

        Logic RAG đã được tách hoàn toàn sang Chatbot/services/RAGService.py
        ChatService chỉ handle chat persistence và gọi RAGService
        """
        # Validate chat exists
        chat = ChatDAO.find_by_id(db, chat_id)
        if not chat:
            return {"ok": False, "message": "Chat không tồn tại"}

        # Lấy model info từ database (nếu có)
        model_id = None
        model_obj = None
        llm_model = "gpt-3.5-turbo"  # Default

        if model_name:
            model_obj = ModelDAO.find_by_name(db, model_name)
            if model_obj:
                model_id = model_obj.id
                llm_model = model_obj.api_identifier or "gpt-3.5-turbo"

        # Lưu user message vào DB
        user_msg = MessageDAO.create(db, chat_id, MessageType.user, content)

        # Gọi Chatbot service qua HTTP (microservice architecture)
        try:
            response = requests.post(
                f"{CHATBOT_SERVICE_URL}/api/rag/answer",
                json={
                    "namespace_id": "ptit_docs",
                    "question": content,
                    "top_k": 5,
                    "token_budget": 2000,
                    "model": llm_model  # Pass model from DB
                },
                timeout=30  # 30 seconds timeout
            )
            response.raise_for_status()
            rag_result = response.json()

            # Lấy answer từ RAG result
            bot_response = rag_result.get("answer", "Xin lỗi, tôi không thể trả lời câu hỏi này.")
            citations_count = len(rag_result.get("citations", []))

        except requests.exceptions.RequestException as e:
            # Fallback nếu Chatbot service không available
            print(f"Chatbot service error: {e}")
            bot_response = (
                "Xin lỗi, hệ thống chatbot đang bảo trì. "
                "Vui lòng thử lại sau hoặc liên hệ admin."
            )
            citations_count = 0

        # Lưu bot message vào DB
        bot_msg = MessageDAO.create(
            db,
            chat_id,
            MessageType.assistant,
            bot_response,
            model_id=model_id
        )

        # Return response
        return {
            "ok": True,
            "message": "Gửi tin nhắn thành công",
            "user_message": {
                "id": user_msg.id,
                "type": user_msg.type.value,
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat(),
            },
            "bot_message": {
                "id": bot_msg.id,
                "type": bot_msg.type.value,
                "content": bot_msg.content,
                "model_id": bot_msg.model_id,
                "model_name": model_obj.name if model_obj else None,
                "created_at": bot_msg.created_at.isoformat(),
            },
            "rag_info": {
                "citations_count": citations_count,
            }
        }

    @staticmethod
    def get_models(db: Session):
        """Lấy danh sách models từ database"""
        models = ModelDAO.find_all_active(db)
        return {
            "ok": True,
            "models": [
                {
                    "id": model.id,
                    "name": model.name,
                    "description": model.description,
                    "api_identifier": model.api_identifier,
                }
                for model in models
            ],
        }
