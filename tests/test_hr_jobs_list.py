# tests/test_hr_jobs_list.py
from models import Job


def login_as_company_a(client):
    res = client.post(
        "/passcode",
        data={
            "password": "1111",
            "next": "/hr_jobs_list"
        },
        follow_redirects=False,
    )
    assert res.status_code in (302, 303)



def test_hr_jobs_list_requires_login_redirects_to_passcode(client):
    res = client.get("/hr_jobs_list", follow_redirects=False)
    assert res.status_code == 303
    assert "/passcode" in res.headers["location"]

def test_hr_jobs_list_shows_only_company_jobs(client):
    login_as_company_a(client)

    res = client.get("/hr_jobs_list")
    assert res.status_code == 200

    html = res.text
    # company name appears on the page
    assert "Demo Company A" in html

    # Should include A jobs
    assert "Backend Engineer" in html
    assert "Data Engineer" in html

    # Should NOT include B job
    assert "Frontend Engineer" not in html


def test_delete_job_success_removes_job_and_redirects(client, db_session):
    login_as_company_a(client)

    # find a job that belongs to company A
    job_a = db_session.query(Job).filter(Job.company == "Demo Company A").first()
    assert job_a is not None

    res = client.post(f"/hr_jobs_list/delete/{job_a.id}", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert res.headers["location"] == "/hr_jobs_list"

    # verify deleted in DB
    deleted = db_session.query(Job).filter(Job.id == job_a.id).first()
    assert deleted is None

    # verify not shown in list
    res2 = client.get("/hr_jobs_list")
    assert res2.status_code == 200
    assert job_a.title not in res2.text


def test_delete_job_other_company_forbidden(client, db_session):
    login_as_company_a(client)

    job_b = db_session.query(Job).filter(Job.company == "Demo Company B").first()
    assert job_b is not None

    res = client.post(f"/hr_jobs_list/delete/{job_b.id}", follow_redirects=False)

    # Expect 403 if you implemented the company ownership check (recommended)
    assert res.status_code == 403

    # Ensure not deleted
    still_there = db_session.query(Job).filter(Job.id == job_b.id).first()
    assert still_there is not None
