from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

DATABASE_URL = "postgresql://postgres:agentops123@127.0.0.1:5433/agentops"


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Creates all tables if they don't exist. Run once at startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Provides a database session, auto-closes when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()