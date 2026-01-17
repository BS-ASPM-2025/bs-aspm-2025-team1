from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, password_hash: str) -> bool:
    return pwd_context.verify(plain, password_hash)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)
