from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
import shutil
import os
from fastapi import File, UploadFile
from src.handlepdf import extract_text_from_pdf
from models import Resume
from shared import get_db,engine,Base

templates = Jinja2Templates(directory="templates")
app = FastAPI(title="Resume–Job Matcher")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
@app.get("/upload_resume", include_in_schema=False)
async def hello_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload_resume.html",
        context={"company_name": "YAHA"}  # Pass data to the template here
    )


@app.post("/upload_resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_location = f"{upload_dir}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    text = extract_text_from_pdf(file_location)
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