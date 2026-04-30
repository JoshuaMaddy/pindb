"""Authentication routes: signup, login, logout, OAuth, onboarding.

OAuth callback flow::

    callback -> linked?  yes -> session + redirect /
             \\         no  -> existing email verified? yes -> auto-link
             \\                                         no  -> bounce to /auth/login
             \\          -> stash identity -> /auth/oauth/onboarding

Linking an additional provider to the current logged-in user is triggered
by ``GET /auth/{provider}?link=1``; the callback sees ``link=1`` in the
stashed state and attaches the provider row to the current user instead
of logging in a different one.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from random import SystemRandom
from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.auth import (
    CurrentUser,
    clear_session_cookie,
    hash_password,
    set_session_cookie,
    verify_dummy_password,
    verify_password,
)
from pindb.config import CONFIGURATION
from pindb.database import UserSession, async_session_maker
from pindb.database.user import User
from pindb.database.user_auth_provider import OAuthProvider, UserAuthProvider
from pindb.password_policy import PasswordPolicyError, validate_password
from pindb.rate_limit import rate_limit
from pindb.routes.auth._oauth import (
    OAuthIdentity,
    fetch_identity,
    get_client,
    provider_enabled,
)
from pindb.templates.auth.login import login_page
from pindb.templates.auth.oauth_onboarding import oauth_onboarding_page
from pindb.templates.auth.signup import signup_page

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL = timedelta(days=30)

_ONBOARDING_COOKIE = "pindb_oauth_onboarding"
_LINK_COOKIE = "pindb_oauth_link"
_ONBOARDING_MAX_AGE = 600  # 10 minutes

_rng = SystemRandom()


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(CONFIGURATION.secret_key, salt=salt)


# ---------------------------------------------------------------------------
# Session + username helpers
# ---------------------------------------------------------------------------


async def _create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    async with async_session_maker.begin() as db:
        db.add(
            UserSession(
                token=token,
                user_id=user_id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
                + SESSION_TTL,
            )
        )
    return token


def _sanitize_username_hint(hint: str) -> str:
    cleaned = "".join(ch for ch in hint if ch.isalnum() or ch in "_-.").strip("._-")
    cleaned = cleaned[:30]
    return cleaned or "user"


async def _suggest_username(db: AsyncSession, hint: str) -> str:
    """Suggest a unique username: hint, or hint + 4 random digits if taken.

    Picks up to 8 random suffixes before falling back to larger numbers.
    """
    base = _sanitize_username_hint(hint)
    if (await db.scalars(select(User.id).where(User.username == base))).first() is None:
        return base

    for _ in range(8):
        candidate = f"{base}{_rng.randint(1000, 9999)}"
        if (
            await db.scalars(select(User.id).where(User.username == candidate))
        ).first() is None:
            return candidate

    # Fallback: widen the number space.
    for _ in range(16):
        candidate = f"{base}{_rng.randint(10_000, 999_999)}"
        if (
            await db.scalars(select(User.id).where(User.username == candidate))
        ).first() is None:
            return candidate

    raise RuntimeError("Unable to find a free username after many attempts")


# ---------------------------------------------------------------------------
# Password login / signup / logout
# ---------------------------------------------------------------------------


def _google_enabled() -> bool:
    return provider_enabled(OAuthProvider.google)


def _discord_enabled() -> bool:
    return provider_enabled(OAuthProvider.discord)


def _meta_enabled() -> bool:
    return provider_enabled(OAuthProvider.meta)


def _render_signup(
    request: Request,
    *,
    error: str | None = None,
    password_errors: list[str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return HTMLResponse(
        content=str(
            signup_page(
                request=request,
                error=error,
                password_errors=password_errors,
                google_enabled=_google_enabled(),
                discord_enabled=_discord_enabled(),
                meta_enabled=_meta_enabled(),
            )
        ),
        status_code=status_code,
    )


def _render_login(
    request: Request,
    *,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return HTMLResponse(
        content=str(
            login_page(
                request=request,
                error=error,
                google_enabled=_google_enabled(),
                discord_enabled=_discord_enabled(),
                meta_enabled=_meta_enabled(),
            )
        ),
        status_code=status_code,
    )


@router.get("/signup", response_model=None)
async def get_signup(request: Request) -> HTMLResponse:
    return _render_signup(request)


@router.post(
    "/signup",
    response_model=None,
    dependencies=[Depends(rate_limit("10/hour"))],
)
async def post_signup(
    request: Request,
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    try:
        validate_password(password, username=username, email=email)
    except PasswordPolicyError as exc:
        return _render_signup(
            request,
            error="Password does not meet the policy.",
            password_errors=exc.rules,
            status_code=400,
        )

    # Unified error for both clashes to prevent user / email enumeration.
    signup_clash = "Those sign-up details aren't available."
    async with async_session_maker.begin() as db:
        if (await db.scalars(select(User).where(User.username == username))).first():
            return _render_signup(request, error=signup_clash, status_code=400)
        if (await db.scalars(select(User).where(User.email == email))).first():
            return _render_signup(request, error=signup_clash, status_code=400)
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
        )
        db.add(user)
        await db.flush()
        user_id = user.id

    token: str = await _create_session(user_id)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, token)
    return response


@router.get("/login", response_model=None)
async def get_login(
    request: Request,
    error: str | None = None,
) -> HTMLResponse:
    return _render_login(request, error=error)


@router.post(
    "/login",
    response_model=None,
    dependencies=[Depends(rate_limit("10/minute"))],
)
async def post_login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    async with async_session_maker() as db:
        user: User | None = (
            await db.scalars(select(User).where(User.username == username))
        ).first()

    if user is None or user.hashed_password is None:
        # Burn an Argon2 verify against a dummy hash so missing users cost
        # roughly the same time as bad passwords — closes the timing oracle.
        verify_dummy_password(password)
        return _render_login(
            request, error="Invalid username or password.", status_code=401
        )

    if not verify_password(plain=password, hashed=user.hashed_password):
        return _render_login(
            request, error="Invalid username or password.", status_code=401
        )

    token: str = await _create_session(user.id)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, token)
    return response


@router.post("/logout", response_model=None)
async def post_logout(request: Request) -> RedirectResponse:
    token: str | None = request.cookies.get("session")
    if token:
        async with async_session_maker.begin() as db:
            user_session: UserSession | None = await db.get(UserSession, token)
            if user_session:
                await db.delete(user_session)

    response = RedirectResponse(url="/", status_code=303)
    clear_session_cookie(response)
    return response


# ---------------------------------------------------------------------------
# OAuth: authorize redirect + callback
# ---------------------------------------------------------------------------


def _set_link_intent(response: Response) -> None:
    token = _serializer("link-intent").dumps({"link": True})
    response.set_cookie(
        key=_LINK_COOKIE,
        value=token,
        max_age=_ONBOARDING_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=CONFIGURATION.session_cookie_secure,
    )


def _consume_link_intent(request: Request, response: Response) -> bool:
    token = request.cookies.get(_LINK_COOKIE)
    if not token:
        return False
    response.delete_cookie(_LINK_COOKIE)
    try:
        _serializer("link-intent").loads(token, max_age=_ONBOARDING_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def _stash_identity(response: Response, identity: OAuthIdentity) -> None:
    token = _serializer("oauth-onboarding").dumps(
        {
            "provider": identity.provider.value,
            "provider_user_id": identity.provider_user_id,
            "email": identity.email,
            "email_verified": identity.email_verified,
            "username_hint": identity.username_hint,
            "provider_username": identity.provider_username,
        }
    )
    response.set_cookie(
        key=_ONBOARDING_COOKIE,
        value=token,
        max_age=_ONBOARDING_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=CONFIGURATION.session_cookie_secure,
    )


def _load_stashed_identity(request: Request) -> OAuthIdentity | None:
    token = request.cookies.get(_ONBOARDING_COOKIE)
    if not token:
        return None
    try:
        data = _serializer("oauth-onboarding").loads(token, max_age=_ONBOARDING_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return OAuthIdentity(
        provider=OAuthProvider(data["provider"]),
        provider_user_id=data["provider_user_id"],
        email=data.get("email"),
        email_verified=bool(data.get("email_verified", False)),
        username_hint=data.get("username_hint", "user"),
        provider_username=data.get("provider_username"),
    )


def _clear_stashed_identity(response: Response) -> None:
    response.delete_cookie(_ONBOARDING_COOKIE)


async def _find_user_by_provider(
    db: AsyncSession, provider: OAuthProvider, provider_user_id: str
) -> User | None:
    link = (
        await db.scalars(
            select(UserAuthProvider).where(
                UserAuthProvider.provider == provider,
                UserAuthProvider.provider_user_id == provider_user_id,
            )
        )
    ).first()
    if link is None:
        return None
    return await db.get(User, link.user_id)


def _link_identity_to_user(
    db: AsyncSession, user: User, identity: OAuthIdentity
) -> None:
    db.add(
        UserAuthProvider(
            user_id=user.id,
            provider=identity.provider,
            provider_user_id=identity.provider_user_id,
            provider_email=identity.email,
            provider_username=identity.provider_username,
            email_verified=identity.email_verified,
        )
    )


async def _redirect_with_session(user_id: int, url: str = "/") -> RedirectResponse:
    token = await _create_session(user_id)
    response = RedirectResponse(url=url, status_code=303)
    set_session_cookie(response, token)
    return response


async def _oauth_authorize(
    provider: OAuthProvider,
    request: Request,
    link: bool,
) -> Response:
    if not provider_enabled(provider):
        raise HTTPException(status_code=404, detail="Provider not configured")
    redirect_uri = f"{CONFIGURATION.base_url}/auth/{provider.value}/callback"
    client = await get_client(provider)
    response = await client.authorize_redirect(request, redirect_uri)
    if link:
        _set_link_intent(response)
    return response


async def _oauth_callback(
    provider: OAuthProvider,
    request: Request,
    current_user: User | None,
) -> Response:
    if not provider_enabled(provider):
        raise HTTPException(status_code=404, detail="Provider not configured")

    identity = await fetch_identity(provider, request)
    return await process_identity(request, identity, current_user)


async def process_identity(
    request: Request,
    identity: OAuthIdentity,
    current_user: User | None,
    *,
    link_intent_override: bool | None = None,
) -> Response:
    """Apply the login/link/onboarding rules for a fetched identity.

    ``link_intent_override`` forces the link-to-current-user branch when
    ``True`` (or disables it when ``False``); leave as ``None`` to read
    the link-intent cookie from the request. This is used by the
    test-only OAuth provider to avoid round-tripping a cookie.
    """
    # Peek + consume link-intent cookie; we may write new cookies on the
    # final response so build it late.
    link_response = RedirectResponse(url="/", status_code=303)
    cookie_link_intent = _consume_link_intent(request, link_response)
    link_intent = (
        cookie_link_intent if link_intent_override is None else link_intent_override
    )

    # -- Link-to-current-user branch -----------------------------------------
    if link_intent and current_user is not None:
        async with async_session_maker.begin() as db:
            existing = await _find_user_by_provider(
                db, identity.provider, identity.provider_user_id
            )
            if existing is not None and existing.id != current_user.id:
                # This provider identity is already attached to someone else.
                return _login_flash(
                    request,
                    error="This account is linked to a different user.",
                    status_code=409,
                )
            if existing is None:
                user = await db.get(User, current_user.id)
                assert user is not None
                _link_identity_to_user(db, user, identity)
        # Already logged in — just redirect to the security page with the
        # link-intent cookie cleared.
        response = RedirectResponse(url="/user/me/security", status_code=303)
        return response

    # -- Already-linked branch -----------------------------------------------
    linked_user: User | None = None
    async with async_session_maker() as db:
        linked_user = await _find_user_by_provider(
            db, identity.provider, identity.provider_user_id
        )

    if linked_user is not None:
        return await _redirect_with_session(linked_user.id)

    # -- Email-matches-existing-user branch ---------------------------------
    if identity.email:
        async with async_session_maker.begin() as db:
            email_user = (
                await db.scalars(select(User).where(User.email == identity.email))
            ).first()
            if email_user is not None:
                if identity.email_verified:
                    _link_identity_to_user(db, email_user, identity)
                    user_id = email_user.id
                else:
                    return _login_flash(
                        request,
                        error=(
                            "An account with this email already exists. "
                            "Log in and link this provider from your "
                            "security settings."
                        ),
                        status_code=409,
                    )
            else:
                user_id = None
        if identity.email_verified and user_id is not None:
            return await _redirect_with_session(user_id)

    # -- New-user onboarding branch -----------------------------------------
    response = RedirectResponse(url="/auth/oauth/onboarding", status_code=303)
    _stash_identity(response, identity)
    return response


def _login_flash(
    request: Request, *, error: str, status_code: int = 400
) -> HTMLResponse:
    return _render_login(request, error=error, status_code=status_code)


# Per-provider routes ---------------------------------------------------------


_oauth_deps = [Depends(rate_limit("30/minute"))]


@router.get("/google", response_model=None, dependencies=_oauth_deps)
async def google_login(request: Request, link: int = 0) -> Response:
    return await _oauth_authorize(OAuthProvider.google, request, bool(link))


@router.get("/google/callback", response_model=None, dependencies=_oauth_deps)
async def google_callback(request: Request, current_user: CurrentUser) -> Response:
    return await _oauth_callback(OAuthProvider.google, request, current_user)


@router.get("/discord", response_model=None, dependencies=_oauth_deps)
async def discord_login(request: Request, link: int = 0) -> Response:
    return await _oauth_authorize(OAuthProvider.discord, request, bool(link))


@router.get("/discord/callback", response_model=None, dependencies=_oauth_deps)
async def discord_callback(request: Request, current_user: CurrentUser) -> Response:
    return await _oauth_callback(OAuthProvider.discord, request, current_user)


@router.get("/meta", response_model=None, dependencies=_oauth_deps)
async def meta_login(request: Request, link: int = 0) -> Response:
    return await _oauth_authorize(OAuthProvider.meta, request, bool(link))


@router.get("/meta/callback", response_model=None, dependencies=_oauth_deps)
async def meta_callback(request: Request, current_user: CurrentUser) -> Response:
    return await _oauth_callback(OAuthProvider.meta, request, current_user)


# ---------------------------------------------------------------------------
# OAuth onboarding (first-time signup via OAuth)
# ---------------------------------------------------------------------------


@router.get("/oauth/onboarding", response_model=None)
async def get_oauth_onboarding(request: Request) -> HTMLResponse | RedirectResponse:
    identity = _load_stashed_identity(request)
    if identity is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    async with async_session_maker() as db:
        suggested = await _suggest_username(db, identity.username_hint)

    return HTMLResponse(
        content=str(
            oauth_onboarding_page(
                request=request,
                provider=identity.provider,
                suggested_username=suggested,
                email=identity.email,
            )
        )
    )


@router.post("/oauth/onboarding", response_model=None)
async def post_oauth_onboarding(
    request: Request,
    username: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    identity = _load_stashed_identity(request)
    if identity is None:
        return RedirectResponse(url="/auth/login", status_code=303)

    username = username.strip()
    if not username:
        return _render_onboarding(
            request, identity, username, "Please choose a username."
        )

    async with async_session_maker.begin() as db:
        # Recheck uniqueness — someone could have grabbed the name between
        # GET and POST.
        if (await db.scalars(select(User).where(User.username == username))).first():
            suggested = await _suggest_username(db, identity.username_hint)
            return HTMLResponse(
                content=str(
                    oauth_onboarding_page(
                        request=request,
                        provider=identity.provider,
                        suggested_username=suggested,
                        email=identity.email,
                        error=(
                            f"That username is taken. Try '{suggested}' or "
                            "pick another."
                        ),
                    )
                ),
                status_code=400,
            )

        user = User(username=username, email=identity.email)
        db.add(user)
        await db.flush()
        _link_identity_to_user(db, user, identity)
        user_id = user.id

    token = await _create_session(user_id)
    response = RedirectResponse(url="/", status_code=303)
    set_session_cookie(response, token)
    _clear_stashed_identity(response)
    return response


def _render_onboarding(
    request: Request,
    identity: OAuthIdentity,
    username: str,
    error: str,
) -> HTMLResponse:
    return HTMLResponse(
        content=str(
            oauth_onboarding_page(
                request=request,
                provider=identity.provider,
                suggested_username=username or identity.username_hint,
                email=identity.email,
                error=error,
            )
        ),
        status_code=400,
    )
