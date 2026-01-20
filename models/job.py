"""

SQLAlchemy model for Job with additional fields and weights.

"""

from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, Float
from shared.database import Base


class Job(Base):
    """
    Job model to store job description information.
    Fields:
    - id: Primary key
    - job_text: Text of the job description
    - id_text: Identifier text for the job
    - title: Job title
    - company: Company name
    - required_skills: Skills required for the job
    - degree: Required degree for the job
    - experience: Required experience for the job
    - skills_weight: Weight for skills matching
    - degree_weight: Weight for degree matching
    - experience_weight: Weight for experience matching
    - weight_general: General weight for overall matching
    - created_at: Timestamp of when the job was created
    """
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

    # Weights
    skills_weight = Column(Float, default=1.0)
    degree_weight = Column(Float, default=1.0)
    experience_weight = Column(Float, default=1.0)
    weight_general = Column(Float, default=1.0)

    created_at = Column(DateTime, default=datetime.utcnow)
