import os
import time
from fastapi import Request, HTTPException
from starlette.status import HTTP_303_SEE_OTHER

ROLE_RECRUITER = "recruiter"
ROLE_JOBSEEKER = "jobseeker"

COMPANY_LOGIN_URL = "/company/login"
JOBSEEKER_LOGIN_URL = "/jobseeker/login"

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))


def start_company_session(request: Request, company_id: int, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
    now = int(time.time())
    request.session.clear()
    request.session.update({
        "company_id": int(company_id),
        "role": ROLE_RECRUITER,
        "iat": now,
        "last": now,
        "exp": now + int(ttl_seconds),
    })


def start_jobseeker_session(request: Request, jobseeker_id: int, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
    now = int(time.time())
    request.session.clear()
    request.session.update({
        "jobseeker_id": int(jobseeker_id),
        "role": ROLE_JOBSEEKER,
        "iat": now,
        "last": now,
        "exp": now + int(ttl_seconds),
    })


def require_company_session(request: Request) -> int:
    sess = request.session

    role = sess.get("role")
    company_id = sess.get("company_id")
    exp_raw = sess.get("exp")

    now = int(time.time())

    try:
        exp = int(exp_raw)
    except (TypeError, ValueError):
        exp = 0

    if role != ROLE_RECRUITER or company_id is None or exp <= now:
        request.session.clear()
        raise HTTPException(
            status_code=HTTP_303_SEE_OTHER,
            headers={"Location": COMPANY_LOGIN_URL},
        )

    sess["last"] = now
    sess["exp"] = now + SESSION_TTL_SECONDS

    return int(company_id)


def require_jobseeker_session(request: Request) -> int:
    sess = request.session

    role = sess.get("role")
    jobseeker_id = sess.get("jobseeker_id")
    exp_raw = sess.get("exp")

    now = int(time.time())

    try:
        exp = int(exp_raw)
    except (TypeError, ValueError):
        exp = 0

    if role != ROLE_JOBSEEKER or jobseeker_id is None or exp <= now:
        sess.clear()
        raise HTTPException(
            status_code=HTTP_303_SEE_OTHER,
            headers={"Location": JOBSEEKER_LOGIN_URL},
        )

    sess["last"] = now
    sess["exp"] = now + SESSION_TTL_SECONDS

    return int(jobseeker_id)

def logout(request: Request) -> None:
    request.session.clear()
