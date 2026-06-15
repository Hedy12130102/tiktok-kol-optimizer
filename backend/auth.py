"""
Authentication & tenant resolution for the multi-tenant API.

- Users are stored in data/users.json: {id, email, password_hash, tenant_id, created_at}.
- Passwords are hashed with pbkdf2_sha256 (passlib, pure-python).
- Login issues a JWT (HS256) whose `sub` is the tenant_id.
- `require_tenant` is the dependency every data endpoint depends on: it validates the
  Bearer token, sets the request-scoped tenant (backend/tenancy.py), and returns the id.

Set env JWT_SECRET in production; a dev fallback is used otherwise.
"""
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel

from backend import tenancy

router = APIRouter()

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_JWT_SECRET = os.environ.get("JWT_SECRET", "dev-insecure-secret-change-me")
_JWT_ALG = "HS256"
_TOKEN_TTL = timedelta(days=7)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── User store ────────────────────────────────────────────────────
def _load_users() -> list:
    if not os.path.exists(tenancy.USERS_PATH):
        return []
    with open(tenancy.USERS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: list):
    os.makedirs(os.path.dirname(tenancy.USERS_PATH), exist_ok=True)
    with open(tenancy.USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _find_user(email: str) -> Optional[dict]:
    email = email.strip().lower()
    return next((u for u in _load_users() if u["email"] == email), None)


def _make_token(tenant_id: str, email: str) -> str:
    payload = {
        "sub": tenant_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + _TOKEN_TTL,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALG)


# ── Models ────────────────────────────────────────────────────────
class Credentials(BaseModel):
    email: str
    password: str


# ── Endpoints ─────────────────────────────────────────────────────
@router.post("/auth/register")
def register(req: Credentials):
    """Create a merchant account + an isolated data tenant, and return a token."""
    email = req.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address")
    if len(req.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if _find_user(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    users = _load_users()
    tenant_id = uuid.uuid4().hex
    user = {
        "id": (max((u["id"] for u in users), default=0) + 1),
        "email": email,
        "password_hash": _pwd.hash(req.password),
        "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    _save_users(users)
    tenancy.provision_tenant(tenant_id)

    return {"token": _make_token(tenant_id, email), "email": email}


@router.post("/auth/login")
def login(req: Credentials):
    """Verify credentials and return a token."""
    user = _find_user(req.email)
    if not user or not _pwd.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Heal any tenant whose folder went missing.
    if not tenancy.tenant_exists(user["tenant_id"]):
        tenancy.provision_tenant(user["tenant_id"])
    return {"token": _make_token(user["tenant_id"], user["email"]), "email": user["email"]}


# ── Tenant dependency (async so the contextvar propagates to sync endpoints) ──
async def require_tenant(authorization: Optional[str] = Header(None)) -> str:
    # Test/dev fallback: no token needed when DEFAULT_TENANT is set.
    if tenancy.DEFAULT_TENANT and not authorization:
        tenancy.set_current_tenant(tenancy.DEFAULT_TENANT)
        return tenancy.DEFAULT_TENANT

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    tenant_id = payload.get("sub")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    tenancy.set_current_tenant(tenant_id)
    return tenant_id


@router.get("/auth/me")
def me(tenant_id: str = Depends(require_tenant)):
    user = next((u for u in _load_users() if u["tenant_id"] == tenant_id), None)
    return {"tenant_id": tenant_id, "email": user["email"] if user else None}
