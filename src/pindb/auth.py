from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.sql.selectable import Select

from pindb.audit_events import set_audit_user, set_audit_user_flags
from pindb.database import UserSession
from pindb.database import session_maker as db_session_maker
from pindb.database.user import User

_hasher = PasswordHasher()

SESSION_COOKIE = "session"


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(
    plain: str,
    hashed: str,
) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


# ---------------------------------------------------------------------------
# Session cookie helpers
# ---------------------------------------------------------------------------


def set_session_cookie(
    response: Response,
    token: str,
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # set True in production behind HTTPS
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def get_current_user(request: Request) -> User | None:
    token: str | None = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with db_session_maker() as session:
        user_session: UserSession | None = session.get(UserSession, token)
        if user_session is None:
            return None
        if user_session.expires_at < now:
            session.delete(user_session)
            session.commit()
            return None
        user: User | None = session.get(User, user_session.user_id)
        if user is None:
            return None
        session.expunge(user)
        return user


CurrentUser = Annotated[User | None, Depends(get_current_user)]


def require_user(user: CurrentUser) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


AuthenticatedUser = Annotated[User, Depends(require_user)]


def require_admin(user: AuthenticatedUser) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_editor(user: AuthenticatedUser) -> User:
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
    token: str | None = request.cookies.get(SESSION_COOKIE)
    request.state.user = None

    if token:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with db_session_maker() as session:
            stmt: Select[tuple[UserSession]] = (
                select(UserSession)
                .where(UserSession.token == token)
                .where(UserSession.expires_at > now)
            )
            user_session: UserSession | None = session.scalars(stmt).first()
            if user_session is not None:
                user: User | None = session.get(User, user_session.user_id)
                if user is not None:
                    session.expunge(user)
                    request.state.user = user

    u = request.state.user
    set_audit_user(u.id if u else None)
    set_audit_user_flags(
        is_admin=u.is_admin if u else False,
        is_editor=(u.is_editor or u.is_admin) if u else False,
    )
    return await call_next(request)
