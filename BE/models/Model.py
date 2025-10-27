from sqlalchemy import Column, Integer, String, Text, Boolean
from BE.db.session import Base

class Model(Base):
    __tablename__ = "tblModel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)  # Tên model (vd: ChatGPT 4o)
    description = Column(Text, nullable=True)  # Mô tả model
    is_active = Column(Boolean, default=True, nullable=False)  # Model có đang hoạt động không
    api_identifier = Column(String(100), nullable=True)  # Mã định danh khi gọi API (vd: gpt-4o)
