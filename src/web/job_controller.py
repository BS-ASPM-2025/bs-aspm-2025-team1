import os
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from shared import get_db
from src.security.session import require_company_session
from src.repositories.job_repository import JobRepository
from src.services.job_service import JobService
from src.web.utils.input_normalizer import InputNormalizer as N


router = APIRouter()
templates = Jinja2Templates(directory="templates")

APP_NAME = os.getenv("APP_NAME", "ResuMe")

_job_repo = JobRepository()
_job_service = JobService(_job_repo)


@router.get("/post_job", include_in_schema=False)
async def post_job_page(
    request: Request,
    company_id: int = Depends(require_company_session),
):
    success = request.query_params.get("success") == "1"
    deleted = request.query_params.get("deleted") == "1"

    return templates.TemplateResponse(
        request=request,
        name="post_job.html",
        context={
            "company_name": APP_NAME,
            "company_id": company_id,
            "success": success,
            "deleted": deleted,
        },
    )


@router.post("/post_job", include_in_schema=False)
async def post_job(
    request: Request,
    company_id: int = Depends(require_company_session),
    title: str = Form(...),
    degree: str = Form(...),
    experience: str = Form(...),
    required_skills: str = Form(...),
    job_text: str = Form(...),
    skills_weight: float = Form(1.0),
    degree_weight: float = Form(1.0),
    experience_weight: float = Form(1.0),
    weight_general: float = Form(1.0),
    db: Session = Depends(get_db),
):
    try:
        _job_service.create_offer(
            db,
            company_id=company_id,
            title=title,
            degree=degree,
            experience=experience,
            required_skills=required_skills,
            job_text=job_text,
            skills_weight=skills_weight,
            degree_weight=degree_weight,
            experience_weight=experience_weight,
            weight_general=weight_general,
        )
    except ValueError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)

    return RedirectResponse(url="/jobs/manage?success=1", status_code=303)


@router.get("/post_job_feedback", include_in_schema=False)
async def post_job_feedback_page(
    request: Request,
    company_id: int = Depends(require_company_session),
):
    return templates.TemplateResponse(
        request=request,
        name="post_job_feedback.html",
        context={"company_name": APP_NAME},
    )


@router.get("/jobs/manage", include_in_schema=False)
async def jobs_manage_page(
    request: Request,
    db: Session = Depends(get_db),
    company_id: int = Depends(require_company_session),
):
    jobs = _job_service.list_jobs_for_company(db, company_id)

    return templates.TemplateResponse(
        request=request,
        name="jobs_manage.html",
        context={
            "company_name": APP_NAME,
            "jobs": jobs,
            "success": request.query_params.get("success") == "1",
            "updated": request.query_params.get("updated") == "1",
            "deleted": request.query_params.get("deleted") == "1",
            "error": request.query_params.get("error"),
        },
    )


@router.get("/jobs/{job_id}/edit", include_in_schema=False)
async def job_edit_page(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(require_company_session),
):
    try:
        job = _job_service.get_offer_for_company(db, company_id=company_id, job_id=job_id)
    except PermissionError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)

    desc_marker = "Description:\n"
    raw = job.raw_text or ""
    job_description = raw.split(desc_marker, 1)[1] if desc_marker in raw else raw

    return templates.TemplateResponse(
        request=request,
        name="job_edit.html",
        context={
            "company_name": APP_NAME,
            "job": job,
            "job_description": job_description,
        },
    )


@router.post("/jobs/{job_id}/edit", include_in_schema=False)
async def job_update(
    request: Request,
    job_id: int,
    company_id: int = Depends(require_company_session),
    title: Optional[str] = Form(None),
    degree: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    required_skills: Optional[str] = Form(None),
    job_text: Optional[str] = Form(None),
    skills_weight: Optional[float] = Form(None),
    degree_weight: Optional[float] = Form(None),
    experience_weight: Optional[float] = Form(None),
    weight_general: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    try:
        _job_service.update_offer(
            db,
            company_id=company_id,
            job_id=job_id,
            title=N.normalize_str(title),
            degree=N.normalize_str(degree),
            experience=N.normalize_str(experience),
            required_skills=N.normalize_str(required_skills),
            job_text=N.normalize_str(job_text),
            skills_weight=N.normalize_float(skills_weight),
            degree_weight=N.normalize_float(degree_weight),
            experience_weight=N.normalize_float(experience_weight),
            weight_general=N.normalize_float(weight_general),
        )
    except PermissionError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)

    return RedirectResponse(url="/jobs/manage?updated=1", status_code=303)


@router.post("/jobs/{job_id}/delete", include_in_schema=False)
async def job_delete(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(require_company_session),
):
    try:
        _job_service.delete_offer(db, company_id=company_id, job_id=job_id)
    except PermissionError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)
    except ValueError as e:
        return RedirectResponse(url=f"/jobs/manage?error={quote(str(e))}", status_code=303)

    return RedirectResponse(url="/jobs/manage?deleted=1", status_code=303)
