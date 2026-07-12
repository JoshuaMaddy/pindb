"""The fixed cast of e2e users, seeded into the template database.

Every xdist worker used to sign each of these up over HTTP and then log them in —
once through the form for each browser context, once more for each httpx client.
That is an argon2 hash per signup plus an argon2 verify per login, times six
users, times every worker, and it dominated the suite: session setup ran 10-16s
per worker while no individual test body took longer than 4.5s.

The cast is constant, so it belongs in the template database each worker clones
rather than being rebuilt per worker. Seeding a ``user_sessions`` row alongside
each user means a context or client authenticates by being handed the cookie,
with no login round-trip at all.

Only e2e runs seed these (see ``build_template``), so integration tests still see
a database containing nothing but the currency table.
"""

from __future__ import annotations

from dataclasses import dataclass

# Matches ``pindb.auth.SESSION_COOKIE``. Duplicated rather than imported so the
# fixtures module stays importable without the app package on the path.
SESSION_COOKIE: str = "session"


@dataclass(frozen=True)
class E2EUser:
    """A seeded user plus the session token that authenticates as them."""

    username: str
    password: str
    token: str
    is_admin: bool = False
    is_editor: bool = False

    @property
    def email(self) -> str:
        return f"{self.username}@x.test"

    def cookie(self, base_url: str) -> dict[str, object]:
        """Playwright ``storage_state`` cookie entry for this user's session."""
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        return {
            "name": SESSION_COOKIE,
            "value": self.token,
            "domain": parsed.hostname or "127.0.0.1",
            "path": "/",
            "httpOnly": True,
            "sameSite": "Lax",
            # Session cookies (no expiry) are dropped by storage_state; -1 means
            # "no expiry" to Playwright.
            "expires": -1,
        }

    def storage_state(self, base_url: str) -> dict[str, object]:
        return {"cookies": [self.cookie(base_url)], "origins": []}


# Passwords are still seeded (hashed) so the handful of tests that drive the real
# login form against these accounts keep working.
ADMIN = E2EUser("e2e_admin_pw", "E2e-Admin-Secret-9!", "e2e-tok-admin-pw", True, True)
EDITOR = E2EUser(
    "e2e_editor_pw", "E2e-Editor-Secret-9!", "e2e-tok-editor-pw", False, True
)
EDITOR_2 = E2EUser(
    "e2e_editor_pw_2", "E2e-Editor-Secret-2-9!", "e2e-tok-editor-pw-2", False, True
)
REGULAR = E2EUser(
    "e2e_regular", "E2e-Regular-Secret-9!", "e2e-tok-regular", False, False
)
# The httpx-only pair, kept distinct from the browser cast so a test that mutates
# one cannot perturb the other.
ADMIN_HTTP = E2EUser(
    "e2e_admin", "E2e-Admin-Secret-9!", "e2e-tok-admin-http", True, True
)
EDITOR_HTTP = E2EUser(
    "e2e_editor", "E2e-Editor-Secret-9!", "e2e-tok-editor-http", False, True
)

E2E_USERS: tuple[E2EUser, ...] = (
    ADMIN,
    EDITOR,
    EDITOR_2,
    REGULAR,
    ADMIN_HTTP,
    EDITOR_HTTP,
)

# Bumped whenever the cast or its tokens change, so a cached template built by an
# older checkout is not silently reused without the new rows. Part of the template
# database name.
SEED_VERSION: str = "1"


def seed_e2e_users(sync_url: str) -> None:
    """Insert the e2e cast and a never-expiring session token for each.

    Core INSERTs, not ORM adds: the audit ``before_flush`` would try to stamp
    ``created_at``/``created_by_id`` against a request-scoped ContextVar that has
    no value here.
    """
    from datetime import datetime

    from sqlalchemy import create_engine, insert

    from pindb.database.session import UserSession
    from pindb.database.user import User
    from tests.helpers.passwords import hashed

    now = datetime.now()
    # The template is reused for as long as its alembic head is current — days, on
    # a kept container — so the seeded sessions must not age out mid-run.
    never = datetime(2999, 1, 1)

    engine = create_engine(sync_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                insert(User),
                [
                    {
                        "username": user.username,
                        "email": user.email,
                        "hashed_password": hashed(user.password),
                        "is_admin": user.is_admin,
                        "is_editor": user.is_editor,
                        "created_at": now,
                        "updated_at": now,
                    }
                    for user in E2E_USERS
                ],
            )
            user_ids = {
                username: user_id
                for user_id, username in connection.exec_driver_sql(
                    "SELECT id, username FROM users"
                ).all()
            }
            connection.execute(
                insert(UserSession),
                [
                    {
                        "token": user.token,
                        "user_id": user_ids[user.username],
                        "expires_at": never,
                        "created_at": now,
                    }
                    for user in E2E_USERS
                ],
            )
    finally:
        engine.dispose()
