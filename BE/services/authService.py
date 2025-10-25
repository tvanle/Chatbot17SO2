from sqlalchemy.orm import Session
from ..repositories.UserRepo import UserRepo

class AuthService:
    @staticmethod
    def checkLogin(db: Session, email: str, password: str):
        user = UserRepo.checkUser(db, email, password)
        if not user:
            return {"ok": False, "message": "Email hoặc mật khẩu không đúng"}
        return {
            "ok": True,
            "message": "Đăng nhập thành công",
            "user": {"id": user.id, "name": user.name, "email": user.email},
        }

    @staticmethod
    def register(db: Session, name: str, email: str, password: str):
        existed = UserRepo.find_by_email(db, email)
        if existed:
            return {"ok": False, "message": "Email đã tồn tại"}
        user = UserRepo.create(db, name, email, password)
        return {
            "ok": True,
            "message": "Đăng ký thành công",
            "user": {"id": user.id, "name": user.name, "email": user.email},
        }

    @staticmethod
    def getProfile(db: Session, user_id: int):
        user = UserRepo.find_by_id(db, user_id)
        if not user:
            return {"ok": False, "message": "Người dùng không tồn tại"}
        return {
            "ok": True,
            "profile": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "joined_at": user.created_at.strftime("%d/%m/%Y"),
            },
        }