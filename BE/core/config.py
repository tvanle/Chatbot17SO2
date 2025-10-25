from pydantic import BaseModel
import os
from urllib.parse import quote_plus

class Settings(BaseModel):
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASS: str = os.getenv("DB_PASS", "1235aBc%4003")  # @ == %40
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_NAME: str = os.getenv("DB_NAME", "chatbot")
    CORS_ORIGINS: list[str] = [
        "http://127.0.0.1:5500", "http://localhost:5500",  # VSCode Live Server
        "http://127.0.0.1:3000", "http://localhost:3000",
    ]

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

_db_password_escaped = quote_plus(Settings().DB_PASS) #Mã hóa ký tự đặc biệt trong mật khẩu
DATABASE_URL = (
    f"mysql+pymysql://{Settings().DB_USER}:{_db_password_escaped}"
    f"@{Settings().DB_HOST}:{Settings().DB_PORT}/{Settings().DB_NAME}"
)

settings = Settings()
