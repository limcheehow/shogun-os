"""Authentication routes and session helpers for the Shogun OS web portal.

Passwords use stdlib ``hashlib.scrypt``. Session cookies carry a stateless
HMAC-signed token so authentication does not require a database round-trip on
every request (an optional Session audit row is still written on login).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_config
from database import get_db, get_primary_tenant
from models import Session as DbSession
from models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "shogun_session"
TOKEN_VERSION = 1

# scrypt parameters (N, r, p) — interactive login friendly, still strong
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SCRYPT_SALT_BYTES = 16


# ---------------------------------------------------------------------------
# Password hashing (scrypt)
# ---------------------------------------------------------------------------


def hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
    """Hash a password with scrypt. Returns ``scrypt$N$r$p$salt_b64$hash_b64``."""
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    salt_bytes = salt or secrets.token_bytes(SCRYPT_SALT_BYTES)
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt_bytes,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return "$".join(
        [
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.urlsafe_b64encode(salt_bytes).decode("ascii"),
            base64.urlsafe_b64encode(dk).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verify of a scrypt password hash."""
    try:
        parts = encoded.split("$")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False
        _, n_s, r_s, p_s, salt_b64, hash_b64 = parts
        n, r, p = int(n_s), int(r_s), int(p_s)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(hash_b64.encode("ascii"))
        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
        )
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Stateless HMAC session tokens
# Format: base64url(payload).base64url(sig)
# payload = f"{version}:{user_id}:{issued_at}:{expires_at}:{nonce}"
# ---------------------------------------------------------------------------


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def create_session_token(
    user_id: int,
    *,
    max_age_seconds: Optional[int] = None,
    secret: Optional[str] = None,
) -> str:
    """Create a signed session token for ``user_id``."""
    cfg = get_config()
    secret_key = (secret or cfg.secret_key).encode("utf-8")
    max_age = max_age_seconds if max_age_seconds is not None else cfg.session_max_age_seconds
    now = int(time.time())
    exp = now + int(max_age)
    nonce = secrets.token_hex(8)
    payload = f"{TOKEN_VERSION}:{user_id}:{now}:{exp}:{nonce}"
    payload_b64 = _b64encode(payload.encode("utf-8"))
    sig = hmac.new(secret_key, payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64encode(sig)}"


def verify_session_token(
    token: str,
    *,
    secret: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Validate an HMAC session token. Returns claims or None."""
    try:
        cfg = get_config()
        secret_key = (secret or cfg.secret_key).encode("utf-8")
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(
            secret_key, payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected_sig, _b64decode(sig_b64)):
            return None
        payload = _b64decode(payload_b64).decode("utf-8")
        version_s, user_id_s, iat_s, exp_s, nonce = payload.split(":", 4)
        if int(version_s) != TOKEN_VERSION:
            return None
        exp = int(exp_s)
        if int(time.time()) >= exp:
            return None
        return {
            "user_id": int(user_id_s),
            "iat": int(iat_s),
            "exp": exp,
            "nonce": nonce,
        }
    except Exception:
        return None


def set_session_cookie(response: Response, token: str) -> None:
    """Attach the signed session cookie to a response."""
    cfg = get_config()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=cfg.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=cfg.public_base_url.startswith("https://"),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


def _token_fingerprint(token: str) -> str:
    """Stable short id for audit Session rows (not the raw token)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:48]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(default="", description="Required unless first_login")
    new_password: str = Field(min_length=8, max_length=256)


class UserResponse(BaseModel):
    id: int
    tenant_id: int
    email: str
    name: str
    role: str
    first_login: bool
    oauth_provider: Optional[str] = None
    company_name: Optional[str] = None
    subdomain: Optional[str] = None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _extract_token(request: Request) -> Optional[str]:
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        return cookie
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the HMAC session token."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    claims = verify_session_token(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session"
        )
    user = db.get(User, claims["user_id"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_token(request)
    if not token:
        return None
    claims = verify_session_token(token)
    if not claims:
        return None
    return db.get(User, claims["user_id"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"admin", "owner"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def _user_response(user: User) -> Dict[str, Any]:
    payload = user.to_dict()
    if user.tenant is not None:
        payload["company_name"] = user.tenant.company_name
        payload["subdomain"] = user.tenant.subdomain
    return payload


def _issue_login_response(db: Session, user: User) -> JSONResponse:
    cfg = get_config()
    token = create_session_token(user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=cfg.session_max_age_seconds)
    # Audit trail row (token fingerprint only)
    db.add(
        DbSession(
            user_id=user.id,
            token=_token_fingerprint(token),
            expires_at=expires_at,
        )
    )
    db.commit()
    body = {
        "user": _user_response(user),
        "requires_password_change": bool(user.first_login),
        "token": token,
    }
    response = JSONResponse(content=body)
    set_session_cookie(response, token)
    return response


# ---------------------------------------------------------------------------
# Local email/password
# ---------------------------------------------------------------------------


@router.post("/login")
async def login(body: LoginRequest, db: Session = Depends(get_db)) -> JSONResponse:
    """Authenticate with email + password (scrypt)."""
    tenant = get_primary_tenant(db)
    email = body.email.lower().strip()
    user = db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == email)
    ).scalar_one_or_none()
    if user is None or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_login_response(db, user)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Change password. On first_login, current password may be empty/temp."""
    if user.first_login:
        # First-login force change: if a password exists, still verify when provided
        if user.password_hash and body.current_password:
            if not verify_password(body.current_password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect"
                )
    else:
        if not user.password_hash or not verify_password(
            body.current_password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect"
            )

    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    user.password_hash = hash_password(body.new_password)
    user.first_login = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"ok": True, "user": _user_response(user)}


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return the currently authenticated user."""
    return {"user": _user_response(user)}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Clear the session cookie and purge matching audit rows."""
    token = _extract_token(request)
    if token:
        fp = _token_fingerprint(token)
        row = db.execute(select(DbSession).where(DbSession.token == fp)).scalar_one_or_none()
        if row is not None:
            db.delete(row)
            db.commit()
    clear_session_cookie(response)
    return {"ok": True}


# ---------------------------------------------------------------------------
# OAuth helpers (Authlib AsyncOAuth2Client)
# ---------------------------------------------------------------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

MS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MS_USERINFO_URL = "https://graph.microsoft.com/oidc/userinfo"


def _oauth_state_token(provider: str) -> str:
    """Signed short-lived state parameter for CSRF protection."""
    cfg = get_config()
    nonce = secrets.token_urlsafe(16)
    ts = str(int(time.time()))
    msg = f"{provider}:{ts}:{nonce}"
    sig = hmac.new(cfg.secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()[
        :24
    ]
    return f"{msg}:{sig}"


def _verify_oauth_state(provider: str, state: str, *, max_age: int = 600) -> bool:
    try:
        cfg = get_config()
        parts = state.rsplit(":", 1)
        if len(parts) != 2:
            return False
        msg, sig = parts
        expected = hmac.new(
            cfg.secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256
        ).hexdigest()[:24]
        if not hmac.compare_digest(expected, sig):
            return False
        p, ts_s, _nonce = msg.split(":", 2)
        if p != provider:
            return False
        if abs(int(time.time()) - int(ts_s)) > max_age:
            return False
        return True
    except Exception:
        return False


async def _upsert_oauth_user(
    db: Session,
    *,
    provider: str,
    oauth_id: str,
    email: str,
    name: str,
) -> User:
    tenant = get_primary_tenant(db)
    email_n = email.lower().strip()
    user = db.execute(
        select(User).where(
            User.tenant_id == tenant.id,
            User.oauth_provider == provider,
            User.oauth_id == oauth_id,
        )
    ).scalar_one_or_none()
    if user is None:
        user = db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == email_n)
        ).scalar_one_or_none()
    if user is None:
        # First OAuth login becomes admin if no users exist yet
        existing_count = len(
            list(db.execute(select(User).where(User.tenant_id == tenant.id)).scalars())
        )
        user = User(
            tenant_id=tenant.id,
            email=email_n,
            name=name or email_n.split("@")[0],
            password_hash=None,
            oauth_provider=provider,
            oauth_id=oauth_id,
            role="admin" if existing_count == 0 else "user",
            first_login=False,
        )
        db.add(user)
    else:
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        if name:
            user.name = name
        if not user.email:
            user.email = email_n
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _frontend_redirect(path: str = "/") -> str:
    cfg = get_config()
    # Prefer SPA origin in dev
    base = cfg.public_base_url.rstrip("/")
    if cfg.debug:
        for origin in cfg.cors_origins:
            if ":5173" in origin:
                base = origin.rstrip("/")
                break
    return f"{base}{path}"


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    """Redirect the browser to Google's OIDC authorize endpoint."""
    cfg = get_config()
    if not cfg.google_oauth.client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    state = _oauth_state_token("google")
    params = {
        "client_id": cfg.google_oauth.client_id,
        "response_type": "code",
        "redirect_uri": cfg.google_oauth.redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Response:
    """Handle Google OAuth callback, issue session, redirect to SPA."""
    if error:
        return RedirectResponse(url=_frontend_redirect(f"/login?error={error}"))
    if not code or not state or not _verify_oauth_state("google", state):
        return RedirectResponse(url=_frontend_redirect("/login?error=invalid_state"))

    cfg = get_config()
    try:
        client = AsyncOAuth2Client(
            client_id=cfg.google_oauth.client_id,
            client_secret=cfg.google_oauth.client_secret,
            timeout=20.0,
        )
        try:
            token = await client.fetch_token(
                GOOGLE_TOKEN_URL,
                code=code,
                grant_type="authorization_code",
                redirect_uri=cfg.google_oauth.redirect_uri,
            )
            access_token = token.get("access_token") if isinstance(token, dict) else None
            if not access_token:
                raise RuntimeError("Google token response missing access_token")
            async with httpx.AsyncClient(timeout=20.0) as http:
                resp = await http.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                info = resp.json()
        finally:
            close = getattr(client, "aclose", None)
            if callable(close):
                await close()
    except Exception as exc:
        logger.exception("Google OAuth failed: %s", exc)
        return RedirectResponse(url=_frontend_redirect("/login?error=oauth_failed"))

    oauth_id = str(info.get("sub") or "")
    email = str(info.get("email") or "")
    name = str(info.get("name") or info.get("given_name") or "")
    if not oauth_id or not email:
        return RedirectResponse(url=_frontend_redirect("/login?error=missing_profile"))

    user = await _upsert_oauth_user(
        db, provider="google", oauth_id=oauth_id, email=email, name=name
    )
    session_token = create_session_token(user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=cfg.session_max_age_seconds)
    db.add(
        DbSession(
            user_id=user.id,
            token=_token_fingerprint(session_token),
            expires_at=expires_at,
        )
    )
    db.commit()

    dest = "/onboarding" if user.first_login else "/"
    response = RedirectResponse(url=_frontend_redirect(dest))
    set_session_cookie(response, session_token)
    return response


@router.get("/microsoft/login")
async def microsoft_login() -> RedirectResponse:
    """Redirect the browser to Microsoft's OIDC authorize endpoint."""
    cfg = get_config()
    if not cfg.microsoft_oauth.client_id:
        raise HTTPException(status_code=503, detail="Microsoft OAuth is not configured")
    state = _oauth_state_token("microsoft")
    params = {
        "client_id": cfg.microsoft_oauth.client_id,
        "response_type": "code",
        "redirect_uri": cfg.microsoft_oauth.redirect_uri,
        "scope": "openid email profile User.Read",
        "state": state,
        "response_mode": "query",
    }
    return RedirectResponse(url=f"{MS_AUTH_URL}?{urlencode(params)}")


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Response:
    """Handle Microsoft OAuth callback, issue session, redirect to SPA."""
    if error:
        return RedirectResponse(url=_frontend_redirect(f"/login?error={error}"))
    if not code or not state or not _verify_oauth_state("microsoft", state):
        return RedirectResponse(url=_frontend_redirect("/login?error=invalid_state"))

    cfg = get_config()
    try:
        client = AsyncOAuth2Client(
            client_id=cfg.microsoft_oauth.client_id,
            client_secret=cfg.microsoft_oauth.client_secret,
            timeout=20.0,
        )
        try:
            token = await client.fetch_token(
                MS_TOKEN_URL,
                code=code,
                grant_type="authorization_code",
                redirect_uri=cfg.microsoft_oauth.redirect_uri,
            )
            access_token = token.get("access_token") if isinstance(token, dict) else None
            if not access_token:
                raise RuntimeError("Microsoft token response missing access_token")
            async with httpx.AsyncClient(timeout=20.0) as http:
                resp = await http.get(
                    MS_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                info = resp.json()
        finally:
            close = getattr(client, "aclose", None)
            if callable(close):
                await close()
    except Exception as exc:
        logger.exception("Microsoft OAuth failed: %s", exc)
        return RedirectResponse(url=_frontend_redirect("/login?error=oauth_failed"))

    oauth_id = str(info.get("sub") or info.get("oid") or "")
    email = str(info.get("email") or info.get("preferred_username") or "")
    name = str(info.get("name") or "")
    if not oauth_id or not email:
        return RedirectResponse(url=_frontend_redirect("/login?error=missing_profile"))

    user = await _upsert_oauth_user(
        db, provider="microsoft", oauth_id=oauth_id, email=email, name=name
    )
    session_token = create_session_token(user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=cfg.session_max_age_seconds)
    db.add(
        DbSession(
            user_id=user.id,
            token=_token_fingerprint(session_token),
            expires_at=expires_at,
        )
    )
    db.commit()

    dest = "/onboarding" if user.first_login else "/"
    response = RedirectResponse(url=_frontend_redirect(dest))
    set_session_cookie(response, session_token)
    return response


# ---------------------------------------------------------------------------
# Bootstrap helper (used by install / first-run)
# ---------------------------------------------------------------------------


def ensure_bootstrap_admin(
    db: Session,
    *,
    email: str,
    password: str,
    name: str = "Admin",
) -> User:
    """Create a tenant admin with a hashed password if email is unused."""
    tenant = get_primary_tenant(db)
    email_n = email.lower().strip()
    existing = db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == email_n)
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        tenant_id=tenant.id,
        email=email_n,
        name=name,
        password_hash=hash_password(password),
        role="admin",
        first_login=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
