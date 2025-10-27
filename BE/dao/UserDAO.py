from sqlalchemy.orm import Session
from sqlalchemy import select
from BE.models.User import User

# DAO: Tầng Data Access Object, xử lý truy vấn database
class UserDAO:
    @staticmethod
    def find_by_email(db: Session, email: str) -> User | None:
        return db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    @staticmethod
    def checkUser(db: Session, email: str, password: str) -> User | None:
        # vì không hash nên so sánh trực tiếp password
        stmt = select(User).where(User.email == email, User.password == password)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create(db: Session, name: str, email: str, password: str) -> User:
        u = User(name=name, email=email, password=password)
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    @staticmethod
    def find_by_id(db: Session, user_id: int) -> User | None:
        return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()