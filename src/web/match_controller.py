import os
from urllib.parse import quote

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from shared import get_db
from src.security.session import require_company_session

from src.repositories.job_repository import JobRepository
from src.repositories.resume_repository import ResumeRepository
from src.repositories.match_repository import MatchRepository
from src.services.match_service import MatchService

router = APIRouter()
templates = Jinja2Templates(directory="templates")

APP_NAME = os.getenv("APP_NAME", "ResuMe")

_job_repo = JobRepository()
_resume_repo = ResumeRepository()
_match_repo = MatchRepository()
_match_service = MatchService(_job_repo, _resume_repo, _match_repo)


@router.get("/jobs/{job_id}/matches", include_in_schema=False)
async def job_matches_page(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(require_company_session),
):
    try:
        job, matches = _match_service.list_view_for_job(
            db,
            session_company_id=company_id,
            job_id=job_id,
            limit=50,
        )
    except ValueError as e:
        # consistent redirect style with job_controller
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)
    except PermissionError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="job_matches.html",
        context={
            "company_name": APP_NAME,
            "error": _matches_error_from_query(request),
            "success": _flag(request, "success"),
            "recomputed": _flag(request, "recomputed"),
            "job": job,
            "matches": matches,
        },
    )



@router.post("/jobs/{job_id}/matches/recompute", include_in_schema=False)
async def recompute_job_matches(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(require_company_session),
    top_k: int = Form(50),
    resumes_limit: int | None = Form(None),
):
    try:
        _match_service.recompute_for_job(
            db,
            session_company_id=company_id,
            job_id=job_id,
            top_k=int(top_k),
            resumes_limit=(int(resumes_limit) if resumes_limit is not None else None),
        )
    except PermissionError:
        return RedirectResponse(url=f"/jobs/manage?error={quote('Access denied')}", status_code=303)
    except ValueError:
        return RedirectResponse(url=f"/jobs/manage?error={quote('Job offer not found')}", status_code=303)
    except Exception:
        return RedirectResponse(url=f"/jobs/{job_id}/matches?err=recompute_failed", status_code=303)

    return RedirectResponse(url=f"/jobs/{job_id}/matches?recomputed=1", status_code=303)


def _matches_error_from_query(request: Request) -> str | None:
    err = request.query_params.get("err")
    if err == "recompute_failed":
        return "Failed to compute matches. Please try again."
    if err == "access_denied":
        return "Access denied."
    if err == "not_found":
        return "Job offer not found."
    if err:
        return "Action failed."
    return None


def _flag(request: Request, name: str) -> bool:
    return request.query_params.get(name) == "1"
