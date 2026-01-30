from sqlalchemy.orm import Session
from models.job import Job

def get_jobs_by_company(db: Session, company_id: int):
    return (
        db.query(Job)
        .filter(Job.company_name == company_id)
        .order_by(Job.id.desc())
        .all()
    )

def delete_job(db: Session, job_id: int, company_id: int):
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == company_id).first()
    if not job:
        return False
    db.delete(job)
    db.commit()
    return True
