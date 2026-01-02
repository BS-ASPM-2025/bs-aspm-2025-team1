
from sqlalchemy import Column, Integer, Text, DateTime
from datetime import datetime
from shared.database import Base


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    job_text = Column(Text, nullable=False)
    id_text = Column(Text, nullable=False)
    
    # New fields
    title = Column(Text, nullable=True)
    company = Column(Text, nullable=True)
    required_skills = Column(Text, nullable=True)
    degree = Column(Text, nullable=True)
    experience = Column(Text, nullable=True) # Storing as string for flexibility (e.g. "5+ years")

    created_at = Column(DateTime, default=datetime.utcnow)