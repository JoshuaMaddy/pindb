"""Authentication: password hashing, session cookies, FastAPI dependencies, audit wiring.

Session tokens live in the ``session`` cookie (see ``SESSION_COOKIE``). The
middleware resolves the user without pruning expired rows on every request;
dependencies may delete expired sessions when loading the user for protected routes.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response

from pindb.audit_events import set_audit_user, set_audit_user_flags
from pindb.config import CONFIGURATION
from pindb.database import UserSession
from pindb.database import session_maker as db_session_maker
from pindb.database.user import User

_hasher = PasswordHasher()

# Argon2 hash of a throwaway password, verified against when no user row
# exists to normalize login response times (see verify_password).
_DUMMY_HASH = _hasher.hash("pindb-timing-oracle-dummy-password")

SESSION_COOKIE = "session"


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return an Argon2 hash string suitable for storing on ``User.password_hash``.

    Args:
        plain (str): Plaintext password.

    Returns:
        str: Encoded Argon2 hash.
    """
    return _hasher.hash(plain)


def verify_password(
    plain: str,
    hashed: str,
) -> bool:
    """Check *plain* against a stored Argon2 *hashed* string.

    Args:
        plain (str): Candidate password from the client.
        hashed (str): Previously stored hash from ``hash_password``.

    Returns:
        bool: ``True`` on success, ``False`` on mismatch.
    """
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def verify_dummy_password(plain: str) -> None:
    """Run an Argon2 verify against a throwaway hash and discard the result.

    Call from login when no user row matches so that the total time
    spent per request does not leak whether the username exists.
    """
    try:
        _hasher.verify(_DUMMY_HASH, plain)
    except VerifyMismatchError:
        pass


# ---------------------------------------------------------------------------
# Session cookie helpers
# ---------------------------------------------------------------------------


def set_session_cookie(
    response: Response,
    token: str,
) -> None:
    """Set the HttpOnly login cookie to *token* (``SameSite=lax``, secure flag from config).

    Args:
        response (Response): Outgoing Starlette/FastAPI response.
        token (str): Opaque session id stored in ``user_sessions``.
    """
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=CONFIGURATION.session_cookie_secure,
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the login cookie from the client.

    Args:
        response (Response): Outgoing response (typically a logout redirect).
    """
    response.delete_cookie(key=SESSION_COOKIE)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def _resolve_user_from_token(
    token: str,
    *,
    prune_expired: bool = False,
) -> User | None:
    """Load the User associated with a session token.

    When ``prune_expired`` is True, an expired session row is deleted (used by
    the FastAPI dependency). The middleware skips expired sessions via a WHERE
    clause instead.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with db_session_maker() as session:
        user_session: UserSession | None = session.get(UserSession, token)
        if user_session is None:
            return None
        if user_session.expires_at < now:
            if prune_expired:
                session.delete(user_session)
                session.commit()
            return None
        user: User | None = session.get(User, user_session.user_id)
        if user is None:
            return None
        session.expunge(user)
        return user


def get_current_user(request: Request) -> User | None:
    """Load the user for the ``session`` cookie, pruning expired session rows.

    Args:
        request (Request): Incoming request.

    Returns:
        User | None: Detached ``User`` when the session is valid, else ``None``.
    """
    token: str | None = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return _resolve_user_from_token(token, prune_expired=True)


CurrentUser = Annotated[User | None, Depends(get_current_user)]


def require_user(user: CurrentUser) -> User:
    """Dependency that requires a logged-in user.

    Args:
        user (User | None): Injected current user (may be ``None`` for guests).

    Raises:
        HTTPException: 401 when ``user`` is ``None``.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


AuthenticatedUser = Annotated[User, Depends(require_user)]


def require_admin(user: AuthenticatedUser) -> User:
    """Dependency that requires ``user.is_admin``.

    Args:
        user (User): Authenticated user (never ``None``).

    Raises:
        HTTPException: 403 when the user is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_editor(user: AuthenticatedUser) -> User:
    """Dependency that requires editor or admin privileges.

    Args:
        user (User): Authenticated user (never ``None``).

    Raises:
        HTTPException: 403 when the user is neither editor nor admin.
    """
    if not (user.is_editor or user.is_admin):
        raise HTTPException(status_code=403, detail="Editor access required")
    return user


EditorUser = Annotated[User, Depends(require_editor)]


# ---------------------------------------------------------------------------
# Middleware — attach current user to request.state
# ---------------------------------------------------------------------------


async def attach_user_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Resolve ``request.state.user``, theme, units, and audit ContextVars.

    Args:
        request (Request): Incoming ASGI request.
        call_next (Callable): Next handler.

    Returns:
        Response: Downstream response after audit state is populated.
    """
    token: str | None = request.cookies.get(SESSION_COOKIE)
    request.state.user = None

    if token:
        request.state.user = _resolve_user_from_token(token)

    current_user = request.state.user
    request.state.theme = current_user.theme if current_user is not None else "mocha"
    request.state.dimension_unit = (
        current_user.dimension_unit if current_user is not None else "mm"
    )
    set_audit_user(current_user.id if current_user else None)
    set_audit_user_flags(
        is_admin=current_user.is_admin if current_user else False,
        is_editor=(current_user.is_editor or current_user.is_admin)
        if current_user
        else False,
    )
    return await call_next(request)
