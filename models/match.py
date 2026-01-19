"""

Match model



from datetime import datetime
from sqlalchemy import Column, Integer, Text, Float, DateTime
from shared.database import Base

class Match(Base):

    Match model to store resume-job match information.
    Fields:
    - id: Primary key
    - resume_text: Text of the resume
    - job_text: Text of the job description
    - match_score: Calculated match score
    - created_at: Timestamp of when the match was created


    __tablename__ = "match"

    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(Text, nullable=False)
    job_text = Column(Text, nullable=False)
    match_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
"""