"""

Database setup and session management using SQLAlchemy.

"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///my_database.db"
#
engine = create_engine(DATABASE_URL, echo=True)


# # Create session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session.
    Ensures that the session is properly closed after use.
    Yields:
        db: SQLAlchemy Session

    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
