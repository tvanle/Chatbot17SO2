from sqlalchemy.orm import Session
from sqlalchemy import select
from BE.models.Message import Message, MessageType

class MessageDAO:
    @staticmethod
    def create(db: Session, chat_id: int, msg_type: MessageType, content: str) -> Message:
        message = Message(chat_id=chat_id, type=msg_type, content=content)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def find_by_chat(db: Session, chat_id: int) -> list[Message]:
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def find_by_id(db: Session, message_id: int) -> Message | None:
        return db.execute(select(Message).where(Message.id == message_id)).scalar_one_or_none()
