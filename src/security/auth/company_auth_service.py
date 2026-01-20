from sqlalchemy.orm import Session

from src.models import Company
from src.repositories.company_repository import CompanyRepository
from src.security.passwords import verify_password


class CompanyAuthService:
    def __init__(self, company_repo: CompanyRepository):
        self.company_repo = company_repo

    def authenticate(self, db: Session, company_name: str, raw_password: str) -> Company | None:
        company = self.company_repo.get_by_name(db, company_name)
        if company is None:
            return None

        if not verify_password(raw_password, company.password_hash):
            return None

        return company
