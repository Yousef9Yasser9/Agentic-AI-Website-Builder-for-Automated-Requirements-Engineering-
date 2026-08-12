from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.auth.config import DATABASE_URL, ROOT_DIR


class Base(DeclarativeBase):
    pass


def _sqlite_path(url: str) -> Path | None:
    if url.startswith("sqlite:///"):
        raw = url.replace("sqlite:///", "", 1)
        return Path(raw) if not raw.startswith(":") else None
    return None


db_path = _sqlite_path(DATABASE_URL)
if db_path is not None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from backend.app.auth import models  # noqa: F401
    from backend.app.auth.seed import seed_first_admin

    (ROOT_DIR / ".tmp").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    seed_first_admin()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
