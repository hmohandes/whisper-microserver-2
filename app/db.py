"""SQLAlchemy engine/session + declarative base."""
import urllib.parse
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _engine() -> Any:
    url = settings.database_url
    if url.startswith("postgresql+psycopg2"):
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        qs.setdefault("options", "-c search_path=public")
        new_qs = urllib.parse.urlencode(qs, doseq=True)
        url = url.split("?")[0] + "?" + new_qs
    return create_engine(url, pool_pre_ping=True)


engine = _engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)
    Base.metadata.create_all(bind=engine)
