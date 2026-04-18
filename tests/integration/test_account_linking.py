"""Integration tests for linking and unlinking OAuth providers."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from pindb.database.user import User
from pindb.database.user_auth_provider import OAuthProvider, UserAuthProvider


def _patch_google(monkeypatch, userinfo: dict[str, Any]) -> None:
    class _FakeClient:
        async def authorize_redirect(self, request, redirect_uri):  # noqa: ARG002
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url="/auth/google/callback", status_code=303)

        async def authorize_access_token(self, request):  # noqa: ARG002
            return {"userinfo": userinfo, "access_token": "fake"}

    import pindb.routes.auth._oauth as oauth_mod

    monkeypatch.setattr(oauth_mod, "_google_configured", lambda: True)
    monkeypatch.setattr(oauth_mod._oauth, "google", _FakeClient(), raising=False)


@pytest.mark.integration
class TestLinkProvider:
    def test_link_flow_attaches_provider(
        self, auth_client, test_user, db_session, monkeypatch
    ):
        _patch_google(
            monkeypatch,
            {
                "sub": "google-link-me",
                "email": "test@example.com",
                "email_verified": True,
                "name": "Tester",
            },
        )

        # Step 1: hit /auth/google?link=1 which sets the link-intent cookie.
        start = auth_client.get("/auth/google?link=1", follow_redirects=False)
        assert start.status_code == 303
        assert "pindb_oauth_link" in start.cookies

        # Step 2: callback — because we're logged in and link intent is set,
        # the provider should be attached to test_user and we're sent to
        # /user/me/security, NOT logged out as a different user.
        auth_client.cookies.set("pindb_oauth_link", start.cookies["pindb_oauth_link"])
        callback = auth_client.get("/auth/google/callback", follow_redirects=False)
        assert callback.status_code == 303
        assert callback.headers["location"] == "/user/me/security"

        link = db_session.scalars(
            select(UserAuthProvider).where(
                UserAuthProvider.provider == OAuthProvider.google,
                UserAuthProvider.provider_user_id == "google-link-me",
            )
        ).first()
        assert link is not None
        assert link.user_id == test_user.id


@pytest.mark.integration
class TestUnlinkProvider:
    def test_unlink_succeeds_when_password_set(
        self, auth_client, test_user, db_session
    ):
        db_session.add(
            UserAuthProvider(
                user_id=test_user.id,
                provider=OAuthProvider.discord,
                provider_user_id="discord-1",
                provider_email="x@x.test",
                email_verified=True,
            )
        )
        db_session.flush()

        response = auth_client.post("/user/me/unlink/discord", follow_redirects=False)
        assert response.status_code == 303

        remaining = db_session.scalars(
            select(UserAuthProvider).where(
                UserAuthProvider.user_id == test_user.id,
                UserAuthProvider.provider == OAuthProvider.discord,
            )
        ).first()
        assert remaining is None

    def test_unlink_refuses_when_it_leaves_no_login(
        self, client, db_session, seed_currencies
    ):
        """A user with NO password and only one linked provider cannot unlink."""
        user = User(username="oauthonly", email="oa@example.com")
        db_session.add(user)
        db_session.flush()
        db_session.add(
            UserAuthProvider(
                user_id=user.id,
                provider=OAuthProvider.google,
                provider_user_id="g-solo",
                provider_email="oa@example.com",
                email_verified=True,
            )
        )
        db_session.flush()

        # Create a session cookie manually.
        import secrets
        from datetime import datetime, timedelta, timezone

        from pindb.database.session import UserSession

        token = secrets.token_urlsafe(32)
        db_session.add(
            UserSession(
                token=token,
                user_id=user.id,
                expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(days=1),
            )
        )
        db_session.flush()

        client.cookies.set("session", token)
        response = client.post("/user/me/unlink/google", follow_redirects=False)
        assert response.status_code == 400
        assert "only sign-in method" in response.text.lower()

        still_there = db_session.scalars(
            select(UserAuthProvider).where(UserAuthProvider.user_id == user.id)
        ).first()
        assert still_there is not None
