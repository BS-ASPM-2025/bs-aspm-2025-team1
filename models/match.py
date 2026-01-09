"""

Match model

"""

from sqlalchemy import Column, Integer, Text, Float, DateTime
from datetime import datetime
from shared.database import Base

class Match(Base):

    __tablename__ = "match"

    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(Text, nullable=False)
    job_text = Column(Text, nullable=False)
    match_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)