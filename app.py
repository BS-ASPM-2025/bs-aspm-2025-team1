import os
import shutil
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, Form, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from shared.alembic_runner import upgrade_head
from starlette.middleware import Middleware
from starlette.status import HTTP_302_FOUND
from starlette.middleware.sessions import SessionMiddleware

from shared import get_db
from src.models import Resume

from src.handlepdf import extract_text_from_pdf
from src.web.auth_controller import router as auth_router
from src.web.job_controller import router as job_router
from src.web.resume_controller import router as resume_router

logger = logging.getLogger("startup")

templates = Jinja2Templates(directory="templates")

APP_NAME = os.getenv("APP_NAME", "ResuMe")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-change-me")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.warning("LIFESPAN: running Alembic upgrade_head() ...")
    upgrade_head()
    logger.warning("LIFESPAN: migrations done.")
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
app.include_router(resume_router)
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"company_name": "ResMe"}
    )

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
        raw_text=text,
        source_id_text=file.filename
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