from sqlalchemy import Column, BigInteger, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from BE.db.session import Base

class Chat(Base):
    __tablename__ = "tblChat"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("tblUser.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
