from sqlalchemy.orm import Session
from models import Company

class CompanyRepository:
    def get_by_name(self, db: Session, company_name: str) -> Company | None:
        return (
            db.query(Company)
            .filter(Company.company_name == company_name)
            .one_or_none()
        )
