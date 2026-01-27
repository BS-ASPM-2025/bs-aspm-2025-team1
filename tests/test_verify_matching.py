"""
Test to verify that match records are created in the database after a resume upload.
"""
import pytest
import io
from models.job import Job
from models.match import Match

def test_matching_logic_creates_records(client, db_session):
    """
    Verify that uploading a résumé creates Match records in the database.
    """
    # 1. Setup: Create a dummy job
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
        
        response = client.post("/upload_resume", files=files)
        assert response.status_code == 200 # Redirected to home which returns 200

    # 3. Verify: Check if Match records exist
    matches = db_session.query(Match).all()
    assert len(matches) > 0
    
    # Check if the score is reasonable (should be high for this match)
    match = matches[0]
    assert match.match_score > 0
    print(f"Calculated match score: {match.match_score}")

    # Cleanup
    db_session.delete(job)
    for m in matches:
        db_session.delete(m)
    db_session.commit()
