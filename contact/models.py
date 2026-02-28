from .database import Base
from sqlalchemy import Column, String, Integer, Boolean


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String)
    phone = Column(Integer)
    isActive = Column(Boolean, nullable=True, default=True)