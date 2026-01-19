"""
SQLAlchemy ORM model for storing resume information in the database.

Resume Model:
- id: Primary key, unique identifier for each resume entry.
- resume_text: Text field to store the content of the resume.
- id_text: Text field to store an associated identifier text.
- created_at: Timestamp indicating when the resume entry was created.



from sqlalchemy import Column, Integer, Text, DateTime
from datetime import datetime
from shared.database import Base


class Resume(Base):


    SQLAlchemy ORM model for the Resume table.
    Represents a resume entry with its text, identifier, and creation timestamp.


    __tablename__ = "resume"
    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(Text, nullable=False)
    id_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
"""