import time
from fastapi import Request, HTTPException
from starlette.status import HTTP_303_SEE_OTHER

ROLE_RECRUITER = "recruiter"
ROLE_JOBSEEKER = "jobseeker"

COMPANY_LOGIN_URL = "/company/login"


def start_company_session(request: Request, company_id: int, ttl_seconds: int) -> None:
    now = int(time.time())
    request.session.clear()
    request.session.update({
        "company_id": int(company_id),
        "role": ROLE_RECRUITER,
        "iat": now,
        "exp": now + int(ttl_seconds),
    })

def require_company_session(request: Request) -> int:
    sess = request.session or {}

    role = sess.get("role")
    company_id = sess.get("company_id")
    exp = sess.get("exp")

    now = int(time.time())

    if role != ROLE_RECRUITER or not company_id or not isinstance(exp, int) or exp <= now:
        request.session.clear()
        raise HTTPException(
            status_code=HTTP_303_SEE_OTHER,
            headers={"Location": COMPANY_LOGIN_URL},
        )

    return int(company_id)
