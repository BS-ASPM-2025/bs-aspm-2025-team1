"""
Company model

Represents a company account used for organization authentication.


from sqlalchemy import Column, Integer, Text, DateTime
from datetime import datetime
from shared.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    # Company identity
    company_name = Column(Text, nullable=False, unique=True, index=True)

    # Store hashed password here (string)
    password = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
"""
