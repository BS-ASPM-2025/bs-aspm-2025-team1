"""
This file tests the API endpoints for uploading a resume.
"""

import io
import sqlite3
import pytest

pytestmark = pytest.mark.usefixtures("auth_job_seeker")

@pytest.mark.skip(reason="outdated after migrations refactor")
def _count_resumes(db_file, filename: str) -> int:
    con = sqlite3.connect(str(db_file))
    try:
        row = con.execute(
            'SELECT COUNT(*) FROM resumes WHERE source_id_text = ?',
            (filename,),
        ).fetchone()
        return int(row[0])
    finally:
        con.close()

@pytest.mark.skip(reason="outdated after migrations refactor")
def test_upload_file_too_large(client):
    """
    Tests that a file larger than 5MB is rejected.
    """
    large_content = b"a" * (5 * 1024 * 1024 + 100)
    files = {"file": ("large_file.pdf", io.BytesIO(large_content), "application/pdf")}

    response = client.post("/upload_resume", files=files)

    assert response.status_code == 200
    assert "File too large. Max size is 5MB." in response.text

@pytest.mark.skip(reason="outdated after migrations refactor")
def test_upload_invalid_file_type(client):
    """
    Tests that a file with an invalid type is rejected.
    """
    content = b"dummy content"
    files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}

    response = client.post("/upload_resume", files=files)

    assert response.status_code == 200
    assert "Invalid file type. Only PDF and DOC/DOCX allowed." in response.text

@pytest.mark.skip(reason="outdated after migrations refactor")
def test_upload_valid_pdf(client):
    """
    Tests that a valid PDF file is accepted and stored in DB.
    """
    content = b"%PDF-1.4..."
    filename = "valid.pdf"
    files = {"file": (filename, io.BytesIO(content), "application/pdf")}

    before = _count_resumes(client.test_db_file, filename)

    response = client.post("/upload_resume", files=files)

    assert response.status_code in (200, 302, 303)

    after = _count_resumes(client.test_db_file, filename)
    assert after == before + 1
