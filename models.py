from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"

    id =Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="student", nullable=False)
    phone = Column(String, nullable=False)
    course = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)