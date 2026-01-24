"""

This file tests the API endpoints for uploading a resume.

"""

import io
from models.job import Job
from models.resume import Resume
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
    # Ideally, we check that we landed on the home page, e.g. check for company name
    # assert "We are processing your resume and will show you insights shortly." in response.text



def seed_jobs(db_session):
    # from your_project.models import Job
    jobs = [
        Job(title="A", company="c1", job_text="jt1", id_text="id_A"),
        Job(title="B", company="c2", job_text="jt2", id_text="id_B"),
        Job(title="C", company="c3", job_text="jt3", id_text="id_C"),
        Job(title="D", company="c4", job_text="jt4", id_text="id_D"),
    ]
    db_session.add_all(jobs)
    db_session.commit()
    return jobs

def upload_pdf(client):
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake content")
    files = {"file": ("resume.pdf", fake_pdf, "application/pdf")}
    return client.post("/upload_resume", files=files, follow_redirects=False)

def test_stores_top3_by_score_expected_behavior(client, db_session):
    """
    This test expresses the intended behavior: top 3 by score descending.
    It will FAIL with your current code (because you use results[:3] without sorting),
    and will PASS after you sort results by score desc.
    """
    seed_jobs(db_session)

    r = upload_pdf(client)
    assert r.status_code == 303
    assert r.headers["location"] == "/resume_upload_feedback"

    s = client.get("/_test/session")
    assert s.status_code == 200, f"Failed to get session: {s.status_code} {s.text}"
    data = s.json()["match_results"]

    # Expected top 3 by score: B(90), D(70), C(50)
    titles = [x["title"] for x in data]
    assert titles == ["B", "D", "C"]

def test_edge_case_less_than_3_jobs(client, db_session):
    # from your_project.models import Job
    db_session.add_all([
        Job(title="B", company="c2", job_text="jt2", id_text="id_B"),
        Job(title="A", company="c1", job_text="jt1", id_text="id_A"),
    ])
    db_session.commit()

    r = upload_pdf(client)
    assert r.status_code == 303

    s = client.get("/_test/session")
    data = s.json()["match_results"]
    assert len(data) == 2  # should not crash / should store what exists
