"""

Session management

"""

import os
import time
from fastapi import Request, HTTPException
from starlette.status import HTTP_303_SEE_OTHER

ROLE_RECRUITER = "recruiter"
ROLE_JOBSEEKER = "jobseeker"

COMPANY_LOGIN_URL = "/passcode"

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))


def start_company_session(request: Request, company_id: int, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
    """
    Start a company session
    :param request:
    :param company_id:
    :param ttl_seconds:
    :return: None
    """
    now = int(time.time())
    request.session.clear()
    request.session.update({
        "company_id": int(company_id),
        "role": ROLE_RECRUITER,
        "iat": now,
        "last": now,
        "exp": now + int(ttl_seconds),
    })


def require_company_session(request: Request) -> int:
    """
    Get a company session
    :param request:
    :return: company session id
    """
    sess = request.session

    role = sess.get("role")
    company_id = sess.get("company_id")
    exp = sess.get("exp")

    now = int(time.time())

    if role != ROLE_RECRUITER or company_id is None or not isinstance(exp, int) or exp <= now:
        request.session.clear()
        raise HTTPException(
            status_code=HTTP_303_SEE_OTHER,
            headers={"Location": COMPANY_LOGIN_URL}
        )

    sess["last"] = now
    sess["exp"] = now + SESSION_TTL_SECONDS

    return int(company_id)


def logout(request: Request) -> None:
    """
    Log out a company session
    :param request:
    :return: None
    """
    request.session.clear()