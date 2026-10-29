import secrets

from fastapi import APIRouter, Cookie, HTTPException, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "papertrail_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7

signer = URLSafeTimedSerializer(settings.session_secret, salt="papertrail-owner")


def _cookie_args() -> dict:
    if settings.cross_site_cookies:
        return {"httponly": True, "samesite": "none", "secure": True}
    return {"httponly": True, "samesite": "lax"}


def require_owner(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> None:
    """Every API route needs the owner session."""
    if not session:
        raise HTTPException(401, "Not logged in")
    try:
        signer.loads(session, max_age=SESSION_MAX_AGE)
    except BadSignature as e:
        raise HTTPException(401, "Invalid session") from e


class LoginIn(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginIn, response: Response) -> dict:
    if not settings.app_password:
        raise HTTPException(503, "APP_PASSWORD is not set on the server")
    # Constant-time compare so the password can't be guessed by timing
    if not secrets.compare_digest(body.password.encode(), settings.app_password.encode()):
        raise HTTPException(401, "Wrong password")
    response.set_cookie(
        SESSION_COOKIE, signer.dumps("owner"), max_age=SESSION_MAX_AGE, **_cookie_args()
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, **_cookie_args())
    return {"ok": True}


@router.get("/me")
def me(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict:
    try:
        require_owner(session)
        return {"owner": True}
    except HTTPException:
        return {"owner": False}
