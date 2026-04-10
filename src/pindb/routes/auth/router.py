from httpx._models import Response
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Select

from pindb.auth import (
    clear_session_cookie,
    hash_password,
    set_session_cookie,
    verify_password,
)
from pindb.config import CONFIGURATION
from pindb.database import UserSession, session_maker
from pindb.database.user import User
from pindb.database.user_auth_provider import OAuthProvider, UserAuthProvider
from pindb.templates.auth.login import login_page
from pindb.templates.auth.signup import signup_page

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL = timedelta(days=30)

# ---------------------------------------------------------------------------
# OAuth client setup
# ---------------------------------------------------------------------------

_oauth = OAuth()

if CONFIGURATION.google_client_id and CONFIGURATION.google_client_secret:
    _oauth.register(
        name="google",
        client_id=CONFIGURATION.google_client_id,
        client_secret=CONFIGURATION.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

if CONFIGURATION.discord_client_id and CONFIGURATION.discord_client_secret:
    _oauth.register(
        name="discord",
        client_id=CONFIGURATION.discord_client_id,
        client_secret=CONFIGURATION.discord_client_secret,
        authorize_url="https://discord.com/oauth2/authorize",
        access_token_url="https://discord.com/api/oauth2/token",
        api_base_url="https://discord.com/api/",
        client_kwargs={"scope": "identify email"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with session_maker.begin() as db:
        db.add(
            UserSession(
                token=token,
                user_id=user_id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
                + SESSION_TTL,
            )
        )
    return token


def _find_or_create_oauth_user(
    provider: OAuthProvider,
    provider_user_id: str,
    provider_email: str | None,
    username_hint: str,
) -> User:
    """Find existing user by provider identity or email, or create a new one."""
    with session_maker.begin() as db:
        # 1. Look up by provider identity
        statement: Select[tuple[UserAuthProvider]] = select(UserAuthProvider).where(
            UserAuthProvider.provider == provider,
            UserAuthProvider.provider_user_id == provider_user_id,
        )
        existing_provider = db.scalars(statement).first()
        if existing_provider is not None:
            user: User | None = db.get(User, existing_provider.user_id)
            assert user is not None
            db.expunge(user)
            return user

        # 2. Look up by email
        user: User | None = None
        if provider_email:
            user = db.scalars(select(User).where(User.email == provider_email)).first()

        # 3. Create new user if needed
        if user is None:
            username: str = _unique_username(session=db, hint=username_hint)
            user = User(username=username, email=provider_email)
            db.add(user)
            db.flush()  # populate user.id

        # Link this provider to the user
        db.add(
            UserAuthProvider(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
            )
        )
        db.expunge(user)
        return user


def _unique_username(session: Session, hint: str) -> str:
    """Ensure username derived from hint is unique, appending a number if needed."""
    base: str = hint[:50].strip() or "user"
    candidate: str = base
    counter = 1
    while session.scalars(select(User).where(User.username == candidate)).first():
        candidate = f"{base}{counter}"
        counter += 1
    return candidate


# ---------------------------------------------------------------------------
# Login / Signup / Logout
# ---------------------------------------------------------------------------


@router.get("/signup", response_model=None)
def get_signup(request: Request) -> HTMLResponse:
    return HTMLResponse(content=str(signup_page(request=request)))


@router.post("/signup", response_model=None)
def post_signup(
    request: Request,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as db:
        if db.scalars(select(User).where(User.username == username)).first():
            return HTMLResponse(
                content=str(
                    signup_page(request=request, error="Username already taken.")
                ),
                status_code=400,
            )
        if db.scalars(select(User).where(User.email == email)).first():
            return HTMLResponse(
                content=str(
                    signup_page(request=request, error="Email already registered.")
                ),
                status_code=400,
            )
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
        )
        db.add(user)
        db.flush()
        user_id = user.id

    token: str = _create_session(user_id)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, token)
    return response


@router.get("/login", response_model=None)
def get_login(request: Request) -> HTMLResponse:
    return HTMLResponse(content=str(login_page(request=request)))


@router.post("/login", response_model=None)
def post_login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    with session_maker() as db:
        user: User | None = db.scalars(
            select(User).where(User.username == username)
        ).first()

    if user is None or user.hashed_password is None:
        return HTMLResponse(
            content=str(
                login_page(request=request, error="Invalid username or password.")
            ),
            status_code=401,
        )

    if not verify_password(plain=password, hashed=user.hashed_password):
        return HTMLResponse(
            content=str(
                login_page(request=request, error="Invalid username or password.")
            ),
            status_code=401,
        )

    token: str = _create_session(user.id)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, token)
    return response


@router.post("/logout", response_model=None)
def post_logout(request: Request) -> RedirectResponse:
    token: str | None = request.cookies.get("session")
    if token:
        with session_maker.begin() as db:
            user_session: UserSession | None = db.get(UserSession, token)
            if user_session:
                db.delete(user_session)

    response = RedirectResponse(url="/", status_code=303)
    clear_session_cookie(response)
    return response


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


@router.get("/google", response_model=None)
async def google_login(request: Request) -> RedirectResponse:
    redirect_uri = f"{CONFIGURATION.base_url}/auth/google/callback"
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=None)
async def google_callback(request: Request) -> RedirectResponse:
    token = await _oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo") or {}
    provider_user_id = str(user_info.get("sub", ""))
    provider_email = user_info.get("email")
    username_hint = user_info.get("name") or (
        provider_email.split("@")[0] if provider_email else "user"
    )

    user = _find_or_create_oauth_user(
        provider=OAuthProvider.google,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
        username_hint=username_hint,
    )
    session_token: str = _create_session(user.id)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, session_token)
    return response


# ---------------------------------------------------------------------------
# Discord OAuth
# ---------------------------------------------------------------------------


@router.get("/discord", response_model=None)
async def discord_login(request: Request) -> RedirectResponse:
    redirect_uri = f"{CONFIGURATION.base_url}/auth/discord/callback"
    return await _oauth.discord.authorize_redirect(request, redirect_uri)


@router.get("/discord/callback", response_model=None)
async def discord_callback(request: Request) -> RedirectResponse:
    token_data = await _oauth.discord.authorize_access_token(request)
    async with httpx.AsyncClient() as client:
        resp: Response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
    resp.raise_for_status()
    userinfo = resp.json()
    provider_user_id = str(userinfo["id"])
    provider_email = userinfo.get("email")
    username_hint = userinfo.get("username") or (
        provider_email.split("@")[0] if provider_email else "user"
    )

    user = _find_or_create_oauth_user(
        provider=OAuthProvider.discord,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
        username_hint=username_hint,
    )
    session_token = _create_session(user.id)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, session_token)
    return response
