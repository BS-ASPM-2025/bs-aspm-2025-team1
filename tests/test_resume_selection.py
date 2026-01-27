import io
import pytest
import re
import app as main_app
from models.job import Job


def _create_job(db_session, title: str, company: str = "TestCo") -> Job:
    job = Job(
        job_text="Dummy job text",
        id_text=title,
        title=title,
        company=company,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_upload_resume_selects_top_matches_above_min_score(client, db_session, monkeypatch):
    """
    When some jobs have scores >= min_score, the endpoint should:
    - Filter out scores below 20
    - Sort remaining by score desc
    - Keep only top_n (3) matches
    """
    # Arrange: create jobs
    titles = ["Job1", "Job2", "Job3", "Job4"]
    for t in titles:
        _create_job(db_session, title=t)

    scores = {
        "Job1": 10.0,  # below threshold
        "Job2": 25.0,
        "Job3": 30.0,
        "Job4": 40.0,
    }

    def fake_calculate_match_score(resume_text, job):
        return scores[job.title]

    # Monkeypatch the scoring function used in app.upload_resume
    monkeypatch.setattr(main_app, "calculate_match_score", fake_calculate_match_score)

    # Act: upload a dummy PDF resume
    file_data = io.BytesIO(b"dummy pdf content")
    response = client.post(
        "/upload_resume",
        files={"file": ("resume.pdf", file_data, "application/pdf")},
        follow_redirects=True,
    )

    # Assert: request succeeded and only top 3 eligible jobs are shown
    assert response.status_code == 200
    body = response.text

    # Job1 is below min_score (20) and should not appear
    assert "Job1" not in body
    # The remaining three should appear
    assert "Job4" in body
    assert "Job3" in body
    assert "Job2" in body

    # And they should be ordered by score descending: Job4, Job3, Job2
    idx4 = body.index("Job4")
    idx3 = body.index("Job3")
    idx2 = body.index("Job2")
    assert idx4 < idx3 < idx2


def test_upload_resume_fallback_when_no_scores_above_min(client, db_session, monkeypatch):
    """
    When no jobs meet the min_score threshold, the endpoint should fall back
    to returning up to 5 best overall matches (here: all existing jobs).
    """
    titles = ["JobA", "JobB", "JobC"]
    for t in titles:
        _create_job(db_session, title=t)

    # All scores below the min_score (20)
    scores = {
        "JobA": 5.0,
        "JobB": 10.0,
        "JobC": 15.0,
    }

    def fake_calculate_match_score(resume_text, job):
        return scores[job.title]

    monkeypatch.setattr(main_app, "calculate_match_score", fake_calculate_match_score)

    file_data = io.BytesIO(b"dummy pdf content")
    response = client.post(
        "/upload_resume",
        files={"file": ("resume.pdf", file_data, "application/pdf")},
        follow_redirects=True,
    )

    assert response.status_code == 200
    body = response.text

    # Fallback should include all three jobs (since len(results)=3 < 5)
    for title in titles:
        assert title in body


def test_upload_resume_with_many_jobs_limits_to_top_three(client, db_session, monkeypatch):
    """
    When there are many jobs and most are above the min_score,
    only the top 3 by score should be shown.
    """
    titles = [f"Job{i}" for i in range(1, 11)]  # 10 jobs
    for t in titles:
        _create_job(db_session, title=t)

    # All scores above min_score=20, increasing with job index
    scores = {title: 20.0 + i for i, title in enumerate(titles, start=1)}

    def fake_calculate_match_score(resume_text, job):
        return scores[job.title]

    monkeypatch.setattr(main_app, "calculate_match_score", fake_calculate_match_score)

    file_data = io.BytesIO(b"dummy pdf content")
    response = client.post(
        "/upload_resume",
        files={"file": ("resume.pdf", file_data, "application/pdf")},
        follow_redirects=True,
    )

    assert response.status_code == 200
    body = response.text

    # Expect only the three highest scoring jobs (Job10, Job9, Job8)
    assert "Job10" in body
    assert "Job9" in body
    assert "Job8" in body

    # Lower-scoring jobs should not appear
    for low_title in ["Job1", "Job2", "Job3", "Job4", "Job5", "Job6", "Job7"]:   
        assert not re.search(rf"\b{low_title}\b", body)
        # assert f'>{low_title}<' not in the body


def test_upload_resume_three_jobs_all_below_min_score(client, db_session, monkeypatch):
    """
    Explicitly verify behavior when exactly three jobs exist and
    all of them are below min_score: they should still be returned
    by the fallback.
    """
    titles = ["Low1", "Low2", "Low3"]
    for t in titles:
        _create_job(db_session, title=t)

    scores = {
        "Low1": 1.0,
        "Low2": 5.0,
        "Low3": 10.0,
    }

    def fake_calculate_match_score(resume_text, job):
        return scores[job.title]

    monkeypatch.setattr(main_app, "calculate_match_score", fake_calculate_match_score)

    file_data = io.BytesIO(b"dummy pdf content")
    response = client.post(
        "/upload_resume",
        files={"file": ("resume.pdf", file_data, "application/pdf")},
        follow_redirects=True,
    )

    assert response.status_code == 200
    body = response.text

    for title in titles:
        assert title in body

