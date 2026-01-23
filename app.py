"""

Main application file for the Resume–Job Matcher web application.
Sets up FastAPI app, routes, and middleware.

"""

import os
import shutil
from contextlib import asynccontextmanager
from passlib.context import CryptContext
import sqlite3
from fastapi import FastAPI, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse

from shared import get_db, engine, Base
from models import Resume, Job, Match, Company
from src.handlepdf import extract_text_from_pdf
from src.findMatch import calculate_match_score
from src.security.passwords import hash_password
from src.web.auth_controller import router as auth_router
from src.web.job_controller import router as job_router

templates = Jinja2Templates(directory="templates")

DB_PATH = "my_database.db"
APP_NAME = os.getenv("APP_NAME", "ResuMe")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-change-me")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    # Initialize a demo company if it doesn't exist
    db = next(get_db())
    try:
        existing_company = db.query(Company).filter_by(company_name="Demo Company").first()
        if not existing_company:
            demo_company = Company(
                company_name="Demo Company",
                password=hash_password("demo_password123")
            )
            db.add(demo_company)
            db.commit()
            print("Demo company created successfully.")
    except Exception as e:
        print(f"Error creating demo company: {e}")
    finally:
        db.close()
    yield

middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=SESSION_SECRET,
        max_age=SESSION_TTL_SECONDS,
        same_site="lax",
        https_only=False,
    )
]

app = FastAPI(title="Resume–Job Matcher", lifespan=lifespan, middleware=middleware)
app.include_router(auth_router)
app.include_router(job_router)
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
#--------------------------------------------------------------
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
    ALLOWED_TYPES = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    if file.content_type not in ALLOWED_TYPES:
        return templates.TemplateResponse(
            request=request,
            name="upload_resume.html",
            context={"company_name": "ResuMe", "error": "Invalid file type. Only PDF and DOC/DOCX allowed."}
        )

    # Check size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_SIZE:
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
            text = "" # Fail gracefully
    else:
        text = "" # Placeholder for DOC/DOCX extraction later

    resume_test = Resume(
        resume_text=text,
        id_text=file.filename
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

    # Store results in session for display
    request.session["match_results"] = results

    return RedirectResponse(url="/resume_upload_feedback", status_code=303)

#--------------------------------------------------------------

@app.get("/resume_upload_feedback", include_in_schema=False)
async def resume_upload_feedback_page(request: Request):
    """
    Render the resume upload feedback page.
    :param request: FastAPI Request object
    :return: Rendered HTML response
    """
    results = request.session.pop("match_results", [])
    return templates.TemplateResponse(
        request=request,
        name="resume_upload_feedback.html",
        context={
            "company_name": "ResuMe",
            "results": results
        }
    )

#@app.post("/resume_upload_feedback", include_in_schema=False)
#async def resume_upload_feedback_return(password: str = Form(...)):
#    return RedirectResponse(url="/", status_code=303)

#--------------------------------------------------------------
@app.get("/passcode", include_in_schema=False)
async def passcode_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="passcode.html",
        context={"company_name": "ResuMe"}
    )

@app.post("/passcode", include_in_schema=False)
async def passcode_submit(password: str = Form(...)):
    return RedirectResponse(url="/post_job", status_code=303)

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

#--------------------------------------------------------------

def get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.get("/jobs_list", include_in_schema=False)
async def jobs_list(
    request: Request,
    conn: sqlite3.Connection = Depends(get_sqlite_conn)
):
    try:
        cur = conn.execute("""
            SELECT
                id,
                title,
                company,
                degree,
                degree_weight,
                experience,
                required_skills,
                skills_weight,
                job_text
            FROM jobs
            ORDER BY id DESC
        """)
        jobs = cur.fetchall()

        return templates.TemplateResponse(
            "JOBS_LIST.html",
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

