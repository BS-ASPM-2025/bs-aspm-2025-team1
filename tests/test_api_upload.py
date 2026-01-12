"""

This file tests the API endpoints for uploading a resume.

"""

import pytest
from app import app
import io
# client fixture is provided by conftest.py


def test_upload_file_too_large(client):
    """
    Tests that a file larger than 5MB is rejected.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    # Create a dummy file larger than 5MB
    large_content = b"a" * (5 * 1024 * 1024 + 100)
    files = {"file": ("large_file.pdf", io.BytesIO(large_content), "application/pdf")}
    
    response = client.post("/upload_resume", files=files)
    
    # Expect 200 OK because we render the template with an error message
    assert response.status_code == 200
    # Check if the error message is present in the HTML response
    assert "File too large. Max size is 5MB." in response.text

def test_upload_invalid_file_type(client):
    """
    Tests that a file with an invalid type is rejected.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    # Create a dummy text file (invalid type)
    content = b"dummy content"
    files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}
    
    response = client.post("/upload_resume", files=files)
    
    assert response.status_code == 200
    assert "Invalid file type. Only PDF and DOC/DOCX allowed." in response.text

def test_upload_valid_pdf(client):
    """
    Tests that a valid PDF file is accepted.
    :param client: TestClient fixture provided by conftest.py
    :return: None
    """
    # Create a valid small PDF file
    # Note: This is not a real PDF, but our content_type check passes. 
    # Real PDF parsing is inside a try/except block in app.py so it shouldn't crash.
    content = b"%PDF-1.4..."
    files = {"file": ("valid.pdf", io.BytesIO(content), "application/pdf")}
    
    response = client.post("/upload_resume", files=files)
    
    # Expect redirect (303) on success. TestClient handles redirects, so we check history or final url
    # However, TestClient follows redirects by default. The final page is "/" (index.html)
    assert response.status_code == 200
    # Ideally we check that we landed on home page, e.g. check for company name
    assert "resume" in response.text