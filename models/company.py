"""
Company model

Represents a company account used for organization authentication.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime
from shared.database import Base


class Company(Base):
    """
    Company model to store company account information.
    Fields:
    - id: Primary key
    - company_name: Name of the company
    - password: Hashed password for authentication
    - created_at: Timestamp of when the company account was created
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    # Company identity
    company_name = Column(Text, nullable=False, unique=True, index=True)

    # Store hashed password here (string)
    password = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
