from sqlalchemy.orm import Session
from BE.dao.ChatDAO import ChatDAO
from BE.dao.MessageDAO import MessageDAO
from BE.dao.ModelDAO import ModelDAO
from BE.models.Message import MessageType

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
        Gửi message của user và trả về response của bot
        Tạm thời chỉ tạo user message, sau này sẽ tích hợp AI model
        """
        chat = ChatDAO.find_by_id(db, chat_id)
        if not chat:
            return {"ok": False, "message": "Chat không tồn tại"}

        # Tìm model_id từ tên model
        model_id = None
        model_obj = None
        if model_name:
            model_obj = ModelDAO.find_by_name(db, model_name)
            if model_obj:
                model_id = model_obj.id

        # Tạo user message (không lưu model cho user message)
        user_msg = MessageDAO.create(db, chat_id, MessageType.user, content)

        # TODO: Tích hợp AI model để tạo bot response
        # Tạm thời dùng response giả
        bot_response = "Xin chào! Tôi là chatbot hỗ trợ PTIT. Tính năng AI đang được phát triển."
        # Lưu model_id cho bot message
        bot_msg = MessageDAO.create(db, chat_id, MessageType.assistant, bot_response, model_id=model_id)

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
