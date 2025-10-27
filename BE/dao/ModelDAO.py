from sqlalchemy.orm import Session
from sqlalchemy import select
from BE.models.Model import Model

class ModelDAO:
    @staticmethod
    def create(db: Session, name: str, description: str = None, api_identifier: str = None) -> Model:
        model = Model(name=name, description=description, api_identifier=api_identifier, is_active=True)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def find_all_active(db: Session) -> list[Model]:
        """Lấy tất cả models đang hoạt động"""
        stmt = select(Model).where(Model.is_active == True).order_by(Model.id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def find_by_name(db: Session, name: str) -> Model | None:
        """Tìm model theo tên"""
        return db.execute(select(Model).where(Model.name == name)).scalar_one_or_none()

    @staticmethod
    def find_by_id(db: Session, model_id: int) -> Model | None:
        """Tìm model theo ID"""
        return db.execute(select(Model).where(Model.id == model_id)).scalar_one_or_none()

    @staticmethod
    def update_status(db: Session, model_id: int, is_active: bool) -> Model | None:
        """Cập nhật trạng thái hoạt động của model"""
        model = ModelDAO.find_by_id(db, model_id)
        if model:
            model.is_active = is_active
            db.commit()
            db.refresh(model)
        return model
