from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    source_id_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(String, nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    required_skills: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    degree: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    experience: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    skills_weight: Mapped[float] = mapped_column(nullable=False, server_default=text("1.0"))
    degree_weight: Mapped[float] = mapped_column(nullable=False, server_default=text("1.0"))
    experience_weight: Mapped[float] = mapped_column(nullable=False, server_default=text("1.0"))
    weight_general: Mapped[float] = mapped_column(nullable=False, server_default=text("1.0"))

    is_open: Mapped[int] = mapped_column(nullable=False, server_default=text("1"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        CheckConstraint("is_open IN (0, 1)", name="ck_jobs_is_open_01"),
    )
