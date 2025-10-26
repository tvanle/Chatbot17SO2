from sqlalchemy import Column, Integer, String, DateTime, func
from BE.db.session import Base

class User(Base):
    __tablename__ = "tblUser"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)  # theo yêu cầu: không hash
    created_at = Column(DateTime, server_default=func.now())
