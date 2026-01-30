"""

Main application file for the Resume–Job Matcher web application.
Sets up FastAPI app, routes, and middleware.

"""

import os
import shutil
import hashlib
from contextlib import asynccontextmanager

import sqlite3
from typing import Optional
from fastapi import FastAPI, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from starlette.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_400_BAD_REQUEST

from src.repositories.company_repository import CompanyRepository
from src.repositories.job_repository import JobRepository
from src.services.job_service import JobService

from src.security.session import (
    start_company_session,
    require_company_session,
    logout,
    has_valid_company_session,
    # get_safe_next_path,
)

from shared import get_db, engine, Base
from models import Resume, Job, Match, Company, hr_job_query
from src.handlepdf import extract_text_from_pdf
from src.findMatch import calculate_match_score


templates = Jinja2Templates(directory="templates")

_company_repo = CompanyRepository()
_job_repo = JobRepository()
_job_service = JobService(_job_repo, _company_repo)

DB_PATH = "my_database.db"
APP_NAME = os.getenv("APP_NAME", "ResuMe")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-change-me")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))

@asynccontextmanager
async def lifespan(app):
    """
    App startup/shutdown hook.

    - Creates all tables based on SQLAlchemy models (Base.metadata).
    - Optionally seeds a few demo rows into `companies` if table is empty.
    """

    # 1) Create tables (if not exist) according to your SQLAlchemy models
    Base.metadata.create_all(bind=engine)

    # 2) (Optional) Seed demo data only if companies table is empty
    db: Session = next(get_db())
    try:
        existing = db.query(Company).first()
        if not existing:
            db.add_all([
                Company(password="1111", company="Demo Company A"),
                Company(password="2222", company="Demo Company B"),
            ])
            db.commit()
            print("Seeded demo companies into 'companies' table.")
    except Exception as e:
        db.rollback()
        print(f"[lifespan] Error during startup seed: {e}")
    finally:
        db.close()

    # 3) App runs here
    yield

    # 4) Shutdown (nothing special for now)
app = FastAPI(title="Resume–Job Matcher", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=SESSION_TTL_SECONDS,
)
# app.include_router(auth_router)
# app.include_router(job_router)

# for r in app.routes:
#     if getattr(r, "path", None) == "/post_job":
#         print("POST_JOB ROUTE:", r.name, r.endpoint)

@app.get("/")
async def root(request: Request):
    """
    Render the home page.
    :param request: FastAPI Request object
    :return: Rendered HTML response
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"company_name": "ResuMe"}
    )
#UPLOAD_RESUME-------------------------------------------------------------
@app.get("/upload_resume", include_in_schema=False)
async def hello_page(request: Request):
    """
    Render the resume upload page.
    :param request: FastAPI Request object
    :return: Rendered HTML response
    """
    return templates.TemplateResponse(
        request=request,
        name="upload_resume.html",
        context={"company_name": "ResuMe"}  # Pass data to the template here
    )
@app.post("/upload_resume")
async def upload_resume(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Handle resume file upload, validate, extract text, and store in a database.
    :param request: FastAPI Request object
    :param file: Uploaded resume file
    :param db: Database session
    :return: Redirect to feedback page on success or render upload page with error
    """
    #Validation
    allowed_types = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    max_size = 5 * 1024 * 1024  # 5MB

    if file.content_type not in allowed_types:
        return templates.TemplateResponse(
            request=request,
            name="upload_resume.html",
            context={"company_name": "ResuMe", "error": "Invalid file type. Only PDF and DOC/DOCX allowed."}
        )

    # Check size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > max_size:
        return templates.TemplateResponse(
            request=request,
            name="upload_resume.html",
            context={"company_name": "ResuMe", "error": "File too large. Max size is 5MB."}
        )

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_location = f"{upload_dir}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    if file.content_type == "application/pdf":
        try:
            text = extract_text_from_pdf(file_location)
        except Exception:
            text = ""  # Fail gracefully
    else:
        text = ""  # Placeholder for DOC/DOCX extraction later

    # Create a deletion token as the SHA-256 hash of the uploaded resume file.
    # This makes the token deterministic for the exact same file content.
    with open(file_location, "rb") as f:
        file_bytes = f.read()
    delete_token = hashlib.sha256(file_bytes).hexdigest()

    resume_test = Resume(
        resume_text=text,
        id_text=file.filename,
        delete_token=delete_token,
    )
    db.add(resume_test)
    db.commit()
    db.refresh(resume_test)
    # find all matching jobs and store the matches
    jobs = db.query(Job).all()
    results = []
    for job in jobs:
        score = calculate_match_score(text, job)
        match_entry = Match(
            resume_text=text,
            job_text=job.job_text,
            match_score=score
        )
        db.add(match_entry)
        results.append({
            "title": job.title or "Unknown Position",
            "company": job.company or "Unknown Company",
            "score": score
        })
    db.commit()

    # Select top matching jobs based on minimum score and cap
    min_score = 20
    top_n = 3
    sorted_results = sorted(results, key=lambda c: c["score"], reverse=True)
    eligible = [c for c in sorted_results if c["score"] >= min_score]

    selected = eligible[:top_n]

    # Guarantee at least some if many exist
    if len(selected) == 0 and len(sorted_results) > 0:
        # fallback: take the best few even if under threshold
        fallback_n = min(5, len(sorted_results))
        selected = sorted_results[:fallback_n]
    
    

    # Store results and delete a link in the session for display
    request.session["match_results"] = selected
    # Build an absolute-safe path for the delete link (token-based)
    request.session["resume_delete_token"] = delete_token

    return RedirectResponse(url="/resume_upload_feedback", status_code=303)

#UPLOAD_RESUME_FEEDSBACK--------------------------------------------------------------

@app.get("/resume_upload_feedback", include_in_schema=False)
async def resume_upload_feedback_page(request: Request):
    """
    Render the resume upload feedback page.
    :param request: FastAPI Request object
    :return: Rendered HTML response
    """
    results = request.session.pop("match_results", [])
    delete_token = request.session.pop("resume_delete_token", None)

    delete_url = None
    if delete_token:
        delete_url = f"/delete_resume_by_token?token={delete_token}"

    return templates.TemplateResponse(
        request=request,
        name="resume_upload_feedback.html",
        context={
            "company_name": "ResuMe",
            "results": results,
            "delete_url": delete_url,
        }
    )


@app.get("/delete_resume_by_token", include_in_schema=False)
async def delete_resume_by_token(request: Request, token: str, db: Session = Depends(get_db)):
    """
    Delete a resume (and its stored file) using a one-time secret token.
    This allows users to delete their data later via a magic link, without log in.
    """
    # Look up the resume by the provided deletion token
    resume_obj = db.query(Resume).filter(Resume.delete_token == token).first()

    if not resume_obj:
        # Nothing to delete or token already used
        return HTMLResponse(
            "<h2>Resume not found</h2><p>The deletion link is invalid or has already been used.</p>",
            status_code=404,
        )

    # Best-effort: delete the underlying file using id_text as the stored filename
    upload_dir = "uploads"
    file_path = os.path.join(upload_dir, resume_obj.id_text)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            # Fail quietly; we still remove the DB record
            pass

    # Delete the resume record itself
    db.delete(resume_obj)
    db.commit()

    return HTMLResponse(
        "<h2>Resume deleted</h2><p>Your resume and its matches have been removed from our system.</p>",
        status_code=200,
    )

#@app.post("/resume_upload_feedback", include_in_schema=False)
#async def resume_upload_feedback_return(password: str = Form(...)):
#    return RedirectResponse(url="/", status_code=303)

#PASSCODE--------------------------------------------------------------
@app.get("/passcode", include_in_schema=False)
async def passcode_page(request: Request):
    # If already logged in, skip passcode and go straight to target.
    # next_path = get_safe_next_path(request.query_params.get("next"), default="/post_job")
    next_path = request.query_params.get("next")
    if has_valid_company_session(request):
        return RedirectResponse(url=next_path, status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="passcode.html",
        context={"company_name": "ResuMe", "next": next_path}
    )

@app.post("/passcode", include_in_schema=False)
async def passcode_submit(
    request: Request,
    password: str = Form(...),
    next: str = Form("/post_job"),
    db: Session = Depends(get_db),
):
    password = (password or "").strip()
    next_path = next  # ✅ בלי פסיק (לא tuple)

    if not password:
        return templates.TemplateResponse(
            request=request,
            name="passcode.html",
            context={"company_name": "ResuMe", "error": "Please enter a password.", "next": next_path}
        )

    record = db.query(Company).filter(Company.password == password).first()

    if not record:
        return templates.TemplateResponse(
            request=request,
            name="passcode.html",
            context={"company_name": "ResuMe", "error": "Wrong password. Please try again.", "next": next_path}
        )

    start_company_session(request, company_id=record.id)

    request.session["company"] = record.company

    request.session["company_name"] = record.company

    return RedirectResponse(url=next_path, status_code=303)



#logout--------------------------------------------------------------------
@app.get("/logout", include_in_schema=False)
async def logout_route(request: Request):
    """
    Clear the current recruiter/company session and redirect to home.
    """
    logout(request)
    return RedirectResponse(url="/", status_code=303)
#--------------------------------------------------------------------------
if __name__ == '__main__':
    import uvicorn

    # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # db = next(get_db())
    # from models.company import Company
    #
    # demo_company = Company(
    #     company_name="Demo",
    #     password= pwd_context.hash("Demo1234")
    # )
    #
    # # Add and commit to the database
    # db.add(demo_company)
    # db.commit()
    # db.refresh(demo_company)
    uvicorn.run("app:app", port=8000,host='0.0.0.0', reload=False, workers=4)

#JOB_LIST--------------------------------------------------------------

@app.get("/jobs_list", include_in_schema=False)
async def jobs_list(request: Request, db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).all()
        return templates.TemplateResponse(
            "jobs_list.html",
            {
                "request": request,
                "company_name": "ResuMe",
                "jobs": jobs
            }
        )

    except Exception as e:
        print("JOBS_LIST ERROR:", repr(e))
        return HTMLResponse(
            f"<h2>JOBS_LIST ERROR</h2><pre>{repr(e)}</pre>",
            status_code=500
        )

#POST_JOB--------------------------------------------------------
@app.get("/post_job", include_in_schema=False)
async def post_job_page(request: Request, db: Session = Depends(get_db)):
    company_id = require_company_session(request)

    company_obj = db.query(Company).filter(Company.id == company_id).first()

    return templates.TemplateResponse(
        request=request,
        name="post_job.html",
        context={
            "company_name": company_obj.company,
            "company": company_obj.company if company_obj else ""
        }
    )


@app.post("/post_job", include_in_schema=False)
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
        created_job = _job_service.create_offer(
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
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    # Build a best-candidates list (top resumes for this job) and pass it via session
    resumes = db.query(Resume).all()
    candidate_results = []
    for r in resumes:
        score = calculate_match_score(r.resume_text, created_job)
        candidate_results.append({
            "resume_id": r.id,
            "resume_name": r.id_text or f"Resume #{r.id}",
            "score": score,
        })
    candidate_results.sort(key=lambda x: x["score"], reverse=True)

    # Keep a small list for UI (adjust as desired)
    request.session["candidate_results"] = candidate_results[:9]
    request.session["posted_job_title"] = created_job.title or "(untitled)"

    return RedirectResponse(url="/post_job_feedback", status_code=303)


@app.get("/post_job_feedback", include_in_schema=False)
async def post_job_feedback_page(
    request: Request,
    company_id: int = Depends(require_company_session),
    db: Session = Depends(get_db),
):
    company_obj = db.query(Company).filter(Company.id == company_id).first()
    candidates = request.session.pop("candidate_results", [])
    posted_job_title = request.session.pop("posted_job_title", None)

    return templates.TemplateResponse(
        request=request,
        name="post_job_feedback.html",
        context={
            "company_name": company_obj.company if company_obj else APP_NAME,
            "candidates": candidates,
            "job_title": posted_job_title,
        },
    )

#hr_jobs_list--------------------------------------------------
@app.get("/hr_jobs_list", include_in_schema=False)
async def hr_jobs_list(request: Request, db: Session = Depends(get_db)):
    company_id = require_company_session(request)  # נשאר רק ל-auth
    company_name = request.session.get("company")

    jobs = (
        db.query(Job)
        .filter(Job.company == company_name)
        .order_by(Job.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="hr_jobs_list.html",
        context={"jobs": jobs, "company": company_name}
    )

@app.post("/hr_jobs_list/delete/{job_id}")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.delete(job)
    db.commit()

    return RedirectResponse("/jobs_list", status_code=303)