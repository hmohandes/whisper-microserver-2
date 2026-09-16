"""PostgreSQL model for API tokens.

Only the SHA-256 hash is stored. The plain token is shown once at creation time.
"""
import datetime as dt

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # sha256 hex
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # first chars for identification
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
