from sqlalchemy import Column, BigInteger, String, Text, DateTime, func, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from BE.db.session import Base
import enum

class MessageType(enum.Enum):
    user = "user"
    assistant = "assistant"

class Message(Base):
    __tablename__ = "tblMessage"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("tblChat.id"), nullable=False, index=True)
    type = Column(SQLEnum(MessageType), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    chat = relationship("Chat", back_populates="messages")
