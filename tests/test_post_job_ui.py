"""

Integration/UI tests for the post-job flow:
- Company logs in
- Posts a job
- Is redirected to the feedback page
- Candidate cards are displayed.

"""

from unittest.mock import patch

from models.resume import Resume


def _login_company(client):
    """
    Helper to log in the test company and establish a recruiter session.
    """
    r = client.post("/passcode", data={"password": "1234"}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/post_job"


def test_post_job_flow_displays_candidates(client, db_session):
    """
    Full flow: login -> post job -> redirect -> candidates displayed.
    """
    # 1) Seed a couple of resumes in the shared test database
    r1 = Resume(resume_text="Python developer with FastAPI", id_text="Alice Resume")
    r2 = Resume(resume_text="Java developer with Spring", id_text="Bob Resume")
    db_session.add_all([r1, r2])
    db_session.commit()

    # 2) Log in as a company (sets up the recruiter session cookie)
    _login_company(client)

    # 3) Patch calculate_match_score so we get deterministic scores
    with patch("app.calculate_match_score") as mock_score:
        # Called once per resume (order: r1, r2)
        mock_score.side_effect = [92.5, 75.0]

        job_data = {
            "title": "Backend Engineer",
            "degree": "Bachelor",
            "experience": "3",
            "required_skills": "Python, FastAPI",
            "job_text": "We are looking for a backend engineer with Python and FastAPI.",
            # weights – use defaults from the form
            "skills_weight": "1.0",
            "degree_weight": "1.0",
            "experience_weight": "1.0",
            "weight_general": "1.0",
        }

        # follow_redirects=True to land on /post_job_feedback
        response = client.post("/post_job", data=job_data, follow_redirects=True)

    # 4) Verify we are on the feedback page and see candidates
    assert response.status_code == 200
    assert "We Found Your Best Matches" in response.text
    assert "These are the best candidates for" in response.text
    assert "Backend Engineer" in response.text

    # Candidate cards and scores
    assert "Alice Resume" in response.text
    assert "Bob Resume" in response.text
    assert "Match:" in response.text
    assert "%" in response.text


def test_post_job_feedback_without_candidates_shows_empty_state(client):
    """
    When logged in but no candidates are in the session, the empty-state message is shown.
    """
    _login_company(client)

    response = client.get("/post_job_feedback")
    assert response.status_code == 200
    assert "No candidates found yet. Upload resumes first, then post a job again." in response.text

