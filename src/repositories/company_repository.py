from sqlalchemy.orm import Session
from models import Company

class CompanyRepository:
    def get_by_name(self, db: Session, company_name: str) -> Company | None:
        return (
            db.query(Company)
            .filter(Company.company_name == company_name)
            .one_or_none()
        )

    def get_by_id(self, db: Session, company_id: int) -> Company | None:
        return (
            db.query(Company)
            .filter(Company.id == int(company_id))
            .one_or_none()
        )

    def get_name_by_id(self, db: Session, company_id: int) -> str | None:
        company = self.get_by_id(db, company_id)
        return company.company_name if company else None
