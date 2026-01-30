"""

Test to verify that match results are stored in the session and displayed on the feedback page.

"""

import io
from models.job import Job
from models.match import Match

def test_matching_ui_display(client, db_session):
    """
    Verify that match results are stored in the session and displayed on the feedback page.
    """
    # 1. Setup: Create a dummy job in the same test database
    job = Job(
        title="Python Developer",
        company="Tech Corp",
        job_text="Looking for a Python developer with experience in FastAPI.",
        id_text="job1",
        required_skills="python, fastapi"
    )
    db_session.add(job)
    db_session.commit()

    # 2. Upload a matching resume
    # Mock the text extraction to return something that will match the job
    from unittest.mock import patch
    with patch("app.extract_text_from_pdf") as mock_extract:
        mock_extract.return_value = "Python developer with FastAPI experience."
        resume_content = b"dummy pdf content"
        files = {"file": ("resume.pdf", io.BytesIO(resume_content), "application/pdf")}
        
        # TestClient handles cookies (sessions) by default
        # follow_redirects=True to go to /resume_upload_feedback
        response = client.post("/upload_resume", files=files, follow_redirects=True)
        assert response.status_code == 200
    
    # 3. Verify: Check if results are rendered in the HTML
    assert "Python Developer" in response.text
    assert "Tech Corp" in response.text
    assert "Match:" in response.text
    assert "%" in response.text

    # Cleanup
    db_session.delete(job)
    db_session.commit()

def test_no_matches_feedback_direct_access(client):
    """
    Verifies that accessing the feedback page directly shows the 'No matches' message.
    """
    response = client.get("/resume_upload_feedback")
    assert response.status_code == 200
    assert "No matches found at this time" in response.text

def test_multiple_jobs_display(client, db_session):
    """
    Verifies that multiple job matches are displayed on the feedback page.
    """
    # 1. Setup: Create two matching jobs
    job1 = Job(title="Dev 1", company="Alpha", job_text="Python", id_text="j1")
    job2 = Job(title="Dev 2", company="Beta", job_text="Python", id_text="j2")
    db_session.add_all([job1, job2])
    db_session.commit()

    # 2. Upload a matching resume
    from unittest.mock import patch
    with patch("app.extract_text_from_pdf") as mock_extract:
        mock_extract.return_value = "Python developer"
        files = {"file": ("resume.pdf", io.BytesIO(b"content"), "application/pdf")}
        response = client.post("/upload_resume", files=files, follow_redirects=True)
    
    # 3. Verify both are present
    assert response.status_code == 200
    assert "Dev 1" in response.text
    assert "Alpha" in response.text
    assert "Dev 2" in response.text
    assert "Beta" in response.text

    # Cleanup
    db_session.query(Job).delete()
    db_session.commit()

def test_missing_job_fields_display(client, db_session):
    """
    Verifies fallback strings are used when job title or company is missing.
    """
    # Create a job with missing title/company
    job = Job(title=None, company=None, job_text="Python", id_text="j3")
    db_session.add(job)
    db_session.commit()

    from unittest.mock import patch
    with patch("app.extract_text_from_pdf") as mock_extract:
        mock_extract.return_value = "Python"
        files = {"file": ("resume.pdf", io.BytesIO(b"content"), "application/pdf")}
        response = client.post("/upload_resume", files=files, follow_redirects=True)

    assert "Unknown Position" in response.text
    assert "Unknown Company" in response.text

    # Cleanup
    db_session.delete(job)
    db_session.commit()


def test_delete_resume_by_token_invalid(client):
    """
    Verifies that accessing delete with an invalid token shows the error message.
    """
    response = client.get("/delete_resume_by_token?token=invalid-token-12345")
    assert response.status_code == 404
    assert "Resume not found" in response.text
    assert "invalid" in response.text or "already been used" in response.text

