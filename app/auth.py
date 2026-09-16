"""Token generation / verification helpers + FastAPI dependency."""
import datetime as dt
import hashlib
import secrets

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import ApiToken

bearer_scheme = HTTPBearer(auto_error=False)


def generate_token() -> str:
    return "wsp_" + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_token_record(db: Session, name: str, quota: int | None = None) -> tuple[ApiToken, str]:
    plain = generate_token()
    record = ApiToken(name=name, token_hash=hash_token(plain), prefix=plain[:8], quota=quota)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, plain


def verify_token(db: Session, plain_token: str) -> ApiToken | None:
    if not plain_token:
        return None
    return db.query(ApiToken).filter(
        ApiToken.token_hash == hash_token(plain_token),
        ApiToken.revoked.is_(False),
    ).first()


def _touch(db: Session, rec: ApiToken) -> None:
    rec.last_used_at = dt.datetime.now(dt.timezone.utc)
    rec.usage += 1
    db.commit()


def _check_quota(rec: ApiToken) -> bool:
    if rec.quota is not None and rec.usage > rec.quota:
        return False
    return True


async def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> ApiToken:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    rec = verify_token(db, creds.credentials)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked token")
    _touch(db, rec)
    if not _check_quota(rec):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quota exceeded ({rec.usage}/{rec.quota})",
        )
    return rec


async def require_auth_ws(websocket: WebSocket, db: Session) -> ApiToken | None:
    token = websocket.query_params.get("token")
    if not token:
        auth = websocket.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    rec = verify_token(db, token or "")
    if rec is None:
        return None
    _touch(db, rec)
    if not _check_quota(rec):
        return None
    return rec
