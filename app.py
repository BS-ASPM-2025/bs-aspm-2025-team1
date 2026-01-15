import os
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware import Middleware
from starlette.status import HTTP_302_FOUND
from starlette.middleware.sessions import SessionMiddleware

from shared import get_db, engine, Base
from models import Resume, Job
import uuid

from src.handlepdf import extract_text_from_pdf
from src.web.auth_controller import router as auth_router
from src.security.session import require_company_session

templates = Jinja2Templates(directory="templates")

APP_NAME = os.getenv("APP_NAME", "ResuMe")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-change-me")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"company_name": "ResMe"}
    )


@app.get("/post_job", include_in_schema=False)
async def post_job_page(
    request: Request,
    company_id: int = Depends(require_company_session),
):
    success = request.query_params.get("success") == "1"

    return templates.TemplateResponse(
        request=request,
        name="post_job.html",
        context={
            "company_name": "ResMe",
            "success": success,
            "company_id": company_id,
        },
    )

@app.post("/post_job")
async def post_job(
        request: Request,
        title: str = Form(...),
        #company: str = Form(...),
        degree: str = Form(...),
        experience: str = Form(...),
        required_skills: str = Form(...),
        job_text: str = Form(...),
        db: Session = Depends(get_db)
):
    # Combine fields for match algorithm text
    combined_text = f"Title: {title}\nSkills: {required_skills}\nDegree: {degree}\nExperience: {experience}\n\nDescription:\n{job_text}"

    # Create simple ID (in real app use UUID)
    id_text = str(uuid.uuid4())

    new_job = Job(
        title=title,
        #company=company,
        degree=degree,
        experience=experience,
        required_skills=required_skills,
        job_text=combined_text,  # Using combined text for searching logic compatibility
        id_text=id_text
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Redirect home or to confirmation. For now home.
    return RedirectResponse(url="/post_job_feedback", status_code=303)


@app.get("/post_job_feedback", include_in_schema=False)
async def post_job_feedback_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="post_job_feedback.html",
        context={"company_name": "ResuMe"})

@app.get("/upload_resume", include_in_schema=False)
async def hello_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload_resume.html",
        context={"company_name": "ResMe"}  # Pass data to the template here
    )
@app.post("/upload_resume")
async def upload_resume(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):

    #Validation
    ALLOWED_TYPES = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    if file.content_type not in ALLOWED_TYPES:
        return templates.TemplateResponse(
            request=request,
            name="upload_resume.html",
            context={"company_name": "ResMe", "error": "Invalid file type. Only PDF and DOC/DOCX allowed."}
        )

    # Check size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_SIZE:
        return templates.TemplateResponse(
            request=request,
            name="upload_resume.html",
            context={"company_name": "ResMe", "error": "File too large. Max size is 5MB."}
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
    return RedirectResponse(url="/resume_upload_feedback", status_code=303)

@app.get("/resume_upload_feedback", include_in_schema=False)
async def resume_upload_feedback_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="resume_upload_feedback.html",
        context={"company_name": "ResMe"}
    )

#@app.post("/resume_upload_feedback", include_in_schema=False)
#async def resume_upload_feedback_return(password: str = Form(...)):
#    return RedirectResponse(url="/", status_code=303)

@app.get("/passcode", include_in_schema=False)
async def passcode_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="passcode.html",
        context={"company_name": "ResMe"}
    )

@app.post("/passcode", include_in_schema=False)
async def passcode_submit(password: str = Form(...)):
    return RedirectResponse(url="/post_job", status_code=303)

    # Validation
    ALLOWED_TYPES = ["application/pdf", "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    if file.content_type not in ALLOWED_TYPES:
        return templates.TemplateResponse(
            request=request,
            name="upload_resume.html",
            context={"company_name": "ResMe", "error": "Invalid file type. Only PDF and DOC/DOCX allowed."}
        )

    # Check size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > MAX_SIZE:
        return templates.TemplateResponse(
            request=request,
            name="upload_resume.html",
            context={"company_name": "ResMe", "error": "File too large. Max size is 5MB."}
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
    return RedirectResponse(url="/", status_code=303)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("app:app", port=8000,host='0.0.0.0', reload=False, workers=4)