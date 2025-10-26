from sqlalchemy.orm import Session
from BE.dao.ChatDAO import ChatDAO
from BE.dao.MessageDAO import MessageDAO
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
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
        }

    @staticmethod
    def send_message(db: Session, chat_id: int, content: str):
        """
        Gửi message của user và trả về response của bot
        Tạm thời chỉ tạo user message, sau này sẽ tích hợp AI model
        """
        chat = ChatDAO.find_by_id(db, chat_id)
        if not chat:
            return {"ok": False, "message": "Chat không tồn tại"}

        # Tạo user message
        user_msg = MessageDAO.create(db, chat_id, MessageType.user, content)

        # TODO: Tích hợp AI model để tạo bot response
        # Tạm thời dùng response giả
        bot_response = "Xin chào! Tôi là chatbot hỗ trợ PTIT. Tính năng AI đang được phát triển."
        bot_msg = MessageDAO.create(db, chat_id, MessageType.assistant, bot_response)

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
                "created_at": bot_msg.created_at.isoformat(),
            },
        }

    @staticmethod
    def get_models():
        """Lấy danh sách models (mock data, sau này sẽ kết nối với AI service)"""
        return {
            "ok": True,
            "models": [
                {
                    "name": "ChatGPT 4o",
                    "description": "Model mạnh nhất, phù hợp cho các tác vụ phức tạp",
                },
                {
                    "name": "ChatGPT 4o mini",
                    "description": "Model nhanh và tiết kiệm, phù hợp cho hội thoại thông thường",
                },
                {
                    "name": "o1-preview",
                    "description": "Model thử nghiệm với khả năng suy luận cao",
                },
                {
                    "name": "o1-mini",
                    "description": "Phiên bản nhẹ của o1, nhanh hơn",
                },
            ],
        }
