from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from BE.db.session import Base
import enum

class MessageType(enum.Enum):
    user = "user"
    assistant = "assistant"

class Message(Base):
    __tablename__ = "tblMessage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("tblChat.id"), nullable=False, index=True)
    type = Column(SQLEnum(MessageType), nullable=False)
    content = Column(Text, nullable=False)
    model_id = Column(Integer, ForeignKey("tblModel.id"), nullable=True, index=True)  # ID của model AI được sử dụng
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    model = relationship("Model")
