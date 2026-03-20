"""
Database engine and session management.

SQLAlchemy setup:
- Engine: connects to the database (SQLite locally, PostgreSQL in prod)
- SessionLocal: creates database sessions (one per request)
- get_db(): FastAPI dependency that provides a session and closes it after the request
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL

# For SQLite, we need check_same_thread=False to allow FastAPI's async to work.
# PostgreSQL doesn't need this, so we only add it for SQLite.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """
    FastAPI dependency that yields a database session.
    The session is automatically closed when the request finishes.

    Usage in route:
        @router.get("/something")
        def get_something(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
