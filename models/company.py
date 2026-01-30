from sqlalchemy import Column, Integer, String
from shared import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)          # NEW
    password = Column(String, unique=True, nullable=False)      # no longer PK
    company = Column(String, nullable=False)
