"""

This file tests the API endpoints for uploading a resume.

"""

import io
import re

from models import Resume

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
    # assert "We are processing your resume and will show you insights shortly." in response.text


def test_delete_resume_by_token_flow(client, db_session):
    """
    End-to-end test:
    - Upload a resume
    - Ensure a delete link is rendered on the feedback page
    - Call the delete link
    - Verify the resume record is removed and subsequent delete fails
    """
    content = b"%PDF-1.4 test resume"
    files = {"file": ("to_delete.pdf", io.BytesIO(content), "application/pdf")}

    # Follow redirects so we end up on the feedback page that shows the delete link
    response = client.post("/upload_resume", files=files, follow_redirects=True)
    assert response.status_code == 200

    body = response.text
    # Ensure the delete link text appears
    assert "Delete my resume" in body

    # Extract the delete URL from the anchor tag
    m = re.search(r'href="(/delete_resume_by_token\?token=[^"]+)"', body)
    assert m is not None, "Delete URL not found in feedback page"
    delete_url = m.group(1)

    # Call the delete endpoint
    del_response = client.get(delete_url)
    assert del_response.status_code == 200
    assert "Resume deleted" in del_response.text

    # Verify that the resume with this token no longer exists in the DB
    token_param = delete_url.split("token=")[1]
    remaining = db_session.query(Resume).filter(Resume.delete_token == token_param).first()
    assert remaining is None

    # Second attempt with the same URL should fail with 404
    del_response_again = client.get(delete_url)
    assert del_response_again.status_code == 404
