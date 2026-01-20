import sqlite3


def insert_job(db_file: str, **kwargs):
    conn = sqlite3.connect(db_file, check_same_thread=False)
    conn.execute("""
        INSERT INTO jobs (job_text, id_text, title, company, required_skills, degree, experience, skills_weight, degree_weight)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        kwargs.get("job_text", "Some description"),
        kwargs.get("id_text", "job_001"),
        kwargs.get("title", "Senior Software Engineer"),
        kwargs.get("company", "ResMe Inc"),
        kwargs.get("required_skills", "Python, FastAPI, SQL"),
        kwargs.get("degree", "Bachelor"),
        kwargs.get("experience", "3"),
        kwargs.get("skills_weight", 30.0),
        kwargs.get("degree_weight", 40.0),
    ))
    conn.commit()
    conn.close()


def test_jobs_list_returns_200(client, tmp_path):
    # Insert one row into the temp DB used by this test
    db_file = str(tmp_path / "test_my_database.db")
    insert_job(db_file, title="777", company="")

    res = client.get("/jobs_list")
    assert res.status_code == 200

    html = res.text
    assert "Jobs List" in html or "JOBS_LIST" in html
#    assert "Backend Engineer" in html
#    assert "CoolCorp" in html


def test_jobs_list_empty_still_works(client):
    res = client.get("/jobs_list")
    assert res.status_code == 200
    # We don't assume exact empty text; just that the page renders
    assert len(res.text) > 0