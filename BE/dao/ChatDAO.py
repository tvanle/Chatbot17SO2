from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from BE.models.Chat import Chat
from typing import Optional, List

class ChatDAO:
    @staticmethod
    def create(db: Session, user_id: int, title: str) -> Chat:
        chat = Chat(user_id=user_id, title=title)
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat

    @staticmethod
    def find_by_id(db: Session, chat_id: int) -> Optional[Chat]:
        return db.execute(select(Chat).where(Chat.id == chat_id)).scalar_one_or_none()

    @staticmethod
    def find_by_user(db: Session, user_id: int) -> List[Chat]:
        stmt = select(Chat).where(Chat.user_id == user_id).order_by(desc(Chat.updated_at))
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_title(db: Session, chat_id: int, title: str) -> Optional[Chat]:
        chat = ChatDAO.find_by_id(db, chat_id)
        if chat:
            chat.title = title
            db.commit()
            db.refresh(chat)
        return chat

    @staticmethod
    def delete(db: Session, chat_id: int) -> bool:
        chat = ChatDAO.find_by_id(db, chat_id)
        if chat:
            db.delete(chat)
            db.commit()
            return True
        return False
