import os

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from shared import get_db
from src.repositories.company_repository import CompanyRepository
from src.security.auth.company_auth_service import CompanyAuthService
from src.security.session import start_company_session, logout
import os
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter()

templates = Jinja2Templates(directory="templates")

_company_repo = CompanyRepository()
_company_auth_service = CompanyAuthService(_company_repo)

print("AUTH_CONTROLLER FILE:", __file__)

@router.get("/company/login", include_in_schema=False)
async def company_login_page(request: Request):
    err = request.query_params.get("err")

    error_msg = None
    if err == "session_expired":
        error_msg = "Your session expired. Please enter the company password again."
    elif err == "access_denied":
        error_msg = "Access denied."
    elif err == "invalid_credentials":
        error_msg = "Invalid company name or password"
    elif err:
        error_msg = "Login required."

    return templates.TemplateResponse(
        request=request,
        name="company_login.html",
        context={
            "company_name": "ResMe",
            "error": error_msg,
        },
    )


@router.post("/auth/company", include_in_schema=False)
async def auth_company(
    request: Request,
    company_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    company = _company_auth_service.authenticate(db, company_name, password)
    if not company:
        return RedirectResponse(url="/company/login?err=invalid_credentials", status_code=303)

    ttl = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
    start_company_session(request, company_id=company.id, ttl_seconds=ttl)

    return RedirectResponse(url="/jobs/manage", status_code=303)


@router.post("/logout", include_in_schema=False)
async def logout_endpoint(request: Request):
    logout(request)
    return RedirectResponse(url="/", status_code=303)