from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from src.models import Match
from src.repositories.job_repository import JobRepository
from src.repositories.resume_repository import ResumeRepository
from src.repositories.match_repository import MatchRepository
from src.tools.matching_scorer import score_resume_against_job


@dataclass(frozen=True)
class MatchView:
    resume_id: int
    score_percent: int
    skills_match: int
    degree_match: int
    experience_match: int


@dataclass(frozen=True)
class MatchListItemView:
    match_id: int
    resume_id: int
    resume_title: str
    job_seeker_id: Optional[int]
    score_percent: int
    created_at: object 


class MatchService:
    def __init__(
        self,
        job_repo: JobRepository,
        resume_repo: ResumeRepository,
        match_repo: MatchRepository,
    ):
        self.job_repo = job_repo
        self.resume_repo = resume_repo
        self.match_repo = match_repo

    def recompute_for_job(
        self,
        db: Session,
        *,
        session_company_id: int,
        job_id: int,
        top_k: int = 50,
        resumes_limit: Optional[int] = None,
    ) -> list[MatchView]:
        job = self.job_repo.get_by_id(db, job_id)
        if not job:
            raise ValueError("Job offer not found")

        if int(job.company_id) != int(session_company_id):
            raise PermissionError("Job offer does not belong to this company")

        resumes = self.resume_repo.list_all(db, limit=resumes_limit)
        if not resumes:
            self.match_repo.delete_by_job_id(db, job_id)
            return []

        scored = []
        for r in resumes:
            s = score_resume_against_job(r, job)
            scored.append((r.id, s))

        scored.sort(key=lambda x: x[1].total_percent, reverse=True)
        top = scored[: int(top_k)]

        self.match_repo.delete_by_job_id(db, job_id)

        to_insert = [
            Match(
                resume_id=int(resume_id),
                job_id=int(job_id),
                score=float(score.total_percent) / 100.0,
            )
            for (resume_id, score) in top
        ]
        self.match_repo.bulk_create(db, to_insert)

        return [
            MatchView(
                resume_id=int(resume_id),
                score_percent=int(score.total_percent),
                skills_match=int(score.skills_match),
                degree_match=int(score.degree_match),
                experience_match=int(score.experience_match),
            )
            for (resume_id, score) in top
        ]

    def list_for_job(
            self,
            db: Session,
            *,
            session_company_id: int,
            job_id: int,
            limit: int = 50,
    ) -> list[Match]:
        job = self.job_repo.get_by_id(db, job_id)
        if not job:
            raise ValueError("Job offer not found")
        if int(job.company_id) != int(session_company_id):
            raise PermissionError("Job offer does not belong to this company")

        return self.match_repo.list_by_job_id(db, job_id, limit=int(limit))

    def list_view_for_job(
            self,
            db: Session,
            *,
            session_company_id: int,
            job_id: int,
            limit: int = 50,
    ) -> tuple["Job", list[MatchListItemView]]:
        """
        Returns (job, list_of_enriched_match_items) for UI.
        Includes ownership check.
        """
        job = self.job_repo.get_by_id(db, job_id)
        if not job:
            raise ValueError("Job offer not found")
        if int(job.company_id) != int(session_company_id):
            raise PermissionError("Job offer does not belong to this company")

        matches = self.match_repo.list_by_job_id(db, job_id, limit=int(limit))

        items: list[MatchListItemView] = []
        for m in matches:
            resume = self.resume_repo.get_by_id(db, m.resume_id)
            title = (resume.source_id_text if resume else None) or f"Resume #{m.resume_id}"
            items.append(
                MatchListItemView(
                    match_id=int(m.id),
                    resume_id=int(m.resume_id),
                    resume_title=title,
                    job_seeker_id=(int(resume.job_seeker_id) if resume else None),
                    score_percent=int(round((m.score or 0.0) * 100)),
                    created_at=m.created_at,
                )
            )

        return job, items
