from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from src.models import Job, Resume

# TF-IDF + cosine
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class MatchScore:
    total_percent: int
    skills_match: int
    degree_match: int
    experience_match: int


def _safe_text(s: str | None) -> str:
    return (s or "").strip()


def calculate_tfidf_similarity(text1: str, text2: str) -> float:
    """
    Returns cosine similarity in [0.0, 1.0] between two texts using TF-IDF.
    MVP approach: fit vectorizer on the pair (text1, text2).
    """
    text1 = _safe_text(text1)
    text2 = _safe_text(text2)
    if not text1 or not text2:
        return 0.0

    corpus = [text1, text2]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)

    try:
        tfidf = vectorizer.fit_transform(corpus)
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2]).flatten()[0]
        return float(sim)
    except Exception:
        return 0.0


def score_resume_against_job(resume: Resume, job: Job) -> MatchScore:
    """
    Weighted match:
    - Compare resume.raw_text against job.required_skills / degree / experience / raw_text separately (TF-IDF)
    - Multiply each similarity by its weight (if field is empty => weight=0)
    - Total score = weighted_sum / total_weight
    """
    resume_text = _safe_text(getattr(resume, "raw_text", ""))

    if not resume_text:
        return MatchScore(0, 0, 0, 0)

    # Skills
    skills_text = _safe_text(getattr(job, "required_skills", ""))
    if skills_text:
        skills_sim = calculate_tfidf_similarity(resume_text, skills_text)
        skills_weight = float(getattr(job, "skills_weight", 1.0) or 0.0)
    else:
        skills_sim = 0.0
        skills_weight = 0.0

    # Degree
    degree_text = _safe_text(getattr(job, "degree", ""))
    if degree_text:
        degree_sim = calculate_tfidf_similarity(resume_text, degree_text)
        degree_weight = float(getattr(job, "degree_weight", 1.0) or 0.0)
    else:
        degree_sim = 0.0
        degree_weight = 0.0

    # Experience
    exp_text = _safe_text(getattr(job, "experience", ""))
    if exp_text:
        exp_sim = calculate_tfidf_similarity(resume_text, exp_text)
        exp_weight = float(getattr(job, "experience_weight", 1.0) or 0.0)
    else:
        exp_sim = 0.0
        exp_weight = 0.0

    # General (full job text)
    job_text = _safe_text(getattr(job, "raw_text", ""))
    if job_text:
        general_sim = calculate_tfidf_similarity(resume_text, job_text)
        general_weight = float(getattr(job, "weight_general", 1.0) or 0.0)
    else:
        general_sim = 0.0
        general_weight = 0.0

    total_weight = skills_weight + degree_weight + exp_weight + general_weight
    if total_weight <= 0.0:
        return MatchScore(0, 0, 0, 0)

    weighted_sum = (
        skills_sim * skills_weight
        + degree_sim * degree_weight
        + exp_sim * exp_weight
        + general_sim * general_weight
    )
    final_score = weighted_sum / total_weight  # 0..1

    def to_pct(x: float) -> int:
        return max(0, min(100, int(round(x * 100))))

    return MatchScore(
        total_percent=to_pct(final_score),
        skills_match=to_pct(skills_sim),
        degree_match=to_pct(degree_sim),
        experience_match=to_pct(exp_sim),
    )
