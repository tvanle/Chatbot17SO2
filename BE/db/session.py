from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from BE.core.config import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# dependency cho FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
