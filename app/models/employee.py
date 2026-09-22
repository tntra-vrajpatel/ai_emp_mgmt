from sqlalchemy import Column, Integer, Numeric, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employee"

    id = Column(Integer, primary_key=True)
    department = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, unique=True)
    name = Column(String(255), nullable=True)
    salary = Column(Numeric(38, 2), nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
