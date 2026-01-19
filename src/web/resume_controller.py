from fastapi import APIRouter, Request, Depends, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from shared import get_db
from src.security.session import require_jobseeker_session
from src.repositories.resume_repository import ResumeRepository
from src.repositories.jobseeker_repository import JobSeekerRepository
from src.services.resume_service import ResumeService
from src.tools.resume_text_extractor import ResumeExtractionError

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_resume_repo = ResumeRepository()
_jobseeker_repo = JobSeekerRepository()
_resume_service = ResumeService(_resume_repo, _jobseeker_repo)


@router.get("/resumes/manage", include_in_schema=False)
async def resumes_manage_page(request: Request, db: Session = Depends(get_db)):
    job_seeker_id = require_jobseeker_session(request)

    err = request.query_params.get("err")
    error_msg = None
    if err == "upload_failed":
        error_msg = "Failed to upload resume. Please try again."
    elif err == "unsupported_file":
        error_msg = "Unsupported file type. Please upload PDF or TXT (DOCX optional)."
    elif err == "access_denied":
        error_msg = "Access denied."
    elif err == "not_found":
        error_msg = "Resume not found."
    elif err:
        error_msg = "Action failed."

    resumes = _resume_service.list_for_jobseeker(db, job_seeker_id)

    success = request.query_params.get("success") is not None
    deleted = request.query_params.get("deleted") is not None

    return templates.TemplateResponse(
        request=request,
        name="resumes_manage.html",
        context={
            "company_name": "ResMe",
            "error": error_msg,
            "resumes": resumes,
            "success": bool(success),
            "deleted": bool(deleted),
        },
    )


@router.get("/resumes/upload", include_in_schema=False)
async def resume_upload_page(request: Request):
    require_jobseeker_session(request)
    err = request.query_params.get("err")

    error_msg = None
    if err == "title_required":
        error_msg = "Please enter a resume title."
    elif err == "unsupported_file":
        error_msg = "Unsupported file type. Please upload PDF or TXT (DOCX optional)."
    elif err == "upload_failed":
        error_msg = "Failed to upload resume."

    return templates.TemplateResponse(
        request=request,
        name="upload_resume.html",
        context={"company_name": "ResMe", "error": error_msg},
    )


@router.post("/resumes/upload", include_in_schema=False)
async def upload_resume(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    job_seeker_id = require_jobseeker_session(request)

    title = title.strip()
    if not title:
        return RedirectResponse(url="/resumes/upload?err=title_required", status_code=303)

    try:
        await _resume_service.create_from_upload(db, job_seeker_id, file, title)
    except ResumeExtractionError as e:
        msg = str(e).lower()
        if "unsupported" in msg:
            return RedirectResponse(url="/resumes/upload?err=unsupported_file", status_code=303)
        return RedirectResponse(url="/resumes/upload?err=upload_failed", status_code=303)

    return RedirectResponse(url="/resumes/manage?success=1", status_code=303)


@router.post("/resumes/{resume_id}/delete", include_in_schema=False)
async def delete_resume(request: Request, resume_id: int, db: Session = Depends(get_db)):
    job_seeker_id = require_jobseeker_session(request)

    ok = _resume_service.delete_if_owned(db, job_seeker_id, resume_id)
    if not ok:
        resume = _resume_service.get_by_id(db, resume_id)
        if resume is None:
            return RedirectResponse(url="/resumes/manage?err=not_found", status_code=303)
        return RedirectResponse(url="/resumes/manage?err=access_denied", status_code=303)

    return RedirectResponse(url="/resumes/manage?deleted=1", status_code=303)


# NEW: open in new tab and render template
@router.get("/resumes/{resume_id}/text", include_in_schema=False)
async def resume_text_view_page(
    request: Request,
    resume_id: int,
    db: Session = Depends(get_db),
):
    job_seeker_id = require_jobseeker_session(request)

    result = _resume_service.build_resume_text_view(db, job_seeker_id, resume_id)

    if result["status"] == "not_found":
        return templates.TemplateResponse(
            request=request,
            name="resume_text_view.html",
            context={
                "company_name": "ResMe",
                "error": "Resume not found.",
            },
            status_code=404,
        )

    if result["status"] == "access_denied":
        return templates.TemplateResponse(
            request=request,
            name="resume_text_view.html",
            context={
                "company_name": "ResMe",
                "error": "Access denied.",
            },
            status_code=403,
        )

    # ok
    return templates.TemplateResponse(
        request=request,
        name="resume_text_view.html",
        context={
            "company_name": "ResMe",
            "error": None,
            "job_seeker_email": result["job_seeker_email"],
            "resume_title": result["resume_title"],
            "resume_id": result["resume_id"],
            "created_at": result["created_at"],
            "resume_text": result["resume_text"],
        },
    )
