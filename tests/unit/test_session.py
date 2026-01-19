import pytest
from fastapi import HTTPException

import src.security.session as sessmod


class FakeRequest:
    def __init__(self, initial=None):
        self.session = dict(initial or {})


def test_start_company_session_sets_expected_fields(monkeypatch):
    monkeypatch.setattr(sessmod.time, "time", lambda: 1_700_000_000)

    req = FakeRequest({"junk": "x"})
    sessmod.start_company_session(req, company_id=5, ttl_seconds=10)

    s = req.session
    assert "junk" not in s
    assert s["company_id"] == 5
    assert s["role"] == sessmod.ROLE_RECRUITER
    assert s["iat"] == 1_700_000_000
    assert s["last"] == 1_700_000_000
    assert s["exp"] == 1_700_000_010


def test_start_jobseeker_session_sets_expected_fields(monkeypatch):
    monkeypatch.setattr(sessmod.time, "time", lambda: 1_700_000_000)

    req = FakeRequest()
    sessmod.start_jobseeker_session(req, jobseeker_id=9, ttl_seconds=20)

    s = req.session
    assert s["jobseeker_id"] == 9
    assert s["role"] == sessmod.ROLE_JOBSEEKER
    assert s["exp"] == 1_700_000_020


def test_require_company_session_returns_id_and_refreshes_exp(monkeypatch):
    # now = 1000
    monkeypatch.setattr(sessmod.time, "time", lambda: 1000)
    monkeypatch.setattr(sessmod, "SESSION_TTL_SECONDS", 30)

    req = FakeRequest({
        "company_id": 7,
        "role": sessmod.ROLE_RECRUITER,
        "exp": 2000,  # still valid
        "last": 900,
    })

    company_id = sessmod.require_company_session(req)

    assert company_id == 7
    assert req.session["last"] == 1000
    assert req.session["exp"] == 1030  # refreshed


@pytest.mark.parametrize("bad_session", [
    {},  # missing all
    {"role": sessmod.ROLE_RECRUITER, "exp": 9999},  # missing company_id
    {"company_id": 1, "exp": 9999},  # missing role
    {"company_id": 1, "role": "wrong", "exp": 9999},  # wrong role
    {"company_id": 1, "role": sessmod.ROLE_RECRUITER, "exp": 999},  # expired (now=1000)
    {"company_id": 1, "role": sessmod.ROLE_RECRUITER, "exp": "bad"},  # invalid exp
])
def test_require_company_session_invalid_clears_and_redirects(monkeypatch, bad_session):
    monkeypatch.setattr(sessmod.time, "time", lambda: 1000)

    req = FakeRequest(bad_session)

    with pytest.raises(HTTPException) as e:
        sessmod.require_company_session(req)

    assert req.session == {}  # cleared
    exc = e.value
    assert exc.status_code == 303
    assert exc.headers["Location"] == sessmod.COMPANY_LOGIN_URL


def test_require_jobseeker_session_invalid_clears_and_redirects(monkeypatch):
    monkeypatch.setattr(sessmod.time, "time", lambda: 1000)

    req = FakeRequest({"role": sessmod.ROLE_JOBSEEKER, "jobseeker_id": 1, "exp": 999})  # expired

    with pytest.raises(HTTPException) as e:
        sessmod.require_jobseeker_session(req)

    assert req.session == {}
    assert e.value.status_code == 303
    assert e.value.headers["Location"] == sessmod.JOBSEEKER_LOGIN_URL


def test_logout_clears_session():
    req = FakeRequest({"a": 1})
    sessmod.logout(req)
    assert req.session == {}
