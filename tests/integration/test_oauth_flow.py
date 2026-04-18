"""Integration tests for the OAuth callback / onboarding flow.

These don't touch real Google/Discord/Meta — they patch the Authlib
``authorize_access_token`` coroutine and, for Discord/Meta, the outbound
httpx ``get`` call, with canned userinfo payloads. The rest of the flow
(branching on link/email-match/onboarding, session cookie issuance,
persistence to ``user_auth_providers``) is the same as in production.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select

from pindb.auth import hash_password
from pindb.database.user import User
from pindb.database.user_auth_provider import OAuthProvider, UserAuthProvider


def _patch_google(monkeypatch, userinfo: dict[str, Any]) -> None:
    """Return a canned Google userinfo from the OAuth client."""

    class _FakeClient:
        async def authorize_redirect(self, request, redirect_uri):  # noqa: ARG002
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url="/auth/google/callback", status_code=303)

        async def authorize_access_token(self, request):  # noqa: ARG002
            return {"userinfo": userinfo, "access_token": "fake"}

    import pindb.routes.auth._oauth as oauth_mod

    # Ensure Google is "configured".
    monkeypatch.setattr(oauth_mod, "_google_configured", lambda: True)
    monkeypatch.setattr(oauth_mod._oauth, "google", _FakeClient(), raising=False)


@pytest.mark.integration
class TestNewUserOnboarding:
    def test_new_google_user_redirects_to_onboarding(self, client, monkeypatch):
        _patch_google(
            monkeypatch,
            {
                "sub": "google-new-1",
                "email": "newgoogle@example.com",
                "email_verified": True,
                "name": "New Google",
            },
        )
        response = client.get("/auth/google/callback", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/auth/oauth/onboarding"
        # The stash cookie should be set.
        assert "pindb_oauth_onboarding" in response.cookies

    def test_onboarding_creates_user_and_provider_link(self, client, monkeypatch):
        _patch_google(
            monkeypatch,
            {
                "sub": "google-new-2",
                "email": "newgoogle2@example.com",
                "email_verified": True,
                "name": "Onboarder",
            },
        )
        # Step 1: trigger callback to get stash cookie.
        cb = client.get("/auth/google/callback", follow_redirects=False)
        cookie = cb.cookies.get("pindb_oauth_onboarding")
        assert cookie is not None

        # Step 2: submit chosen username.
        client.cookies.set("pindb_oauth_onboarding", cookie)
        resp = client.post(
            "/auth/oauth/onboarding",
            data={"username": "Onboarder"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"
        assert "session" in resp.cookies


@pytest.mark.integration
class TestReturningUserSkipsOnboarding:
    def test_second_login_same_provider_id_goes_home(
        self, client, db_session, seed_currencies, monkeypatch
    ):
        user = User(username="returner", email="ret@example.com")
        db_session.add(user)
        db_session.flush()
        db_session.add(
            UserAuthProvider(
                user_id=user.id,
                provider=OAuthProvider.google,
                provider_user_id="returning-1",
                provider_email="ret@example.com",
                email_verified=True,
            )
        )
        db_session.flush()

        _patch_google(
            monkeypatch,
            {
                "sub": "returning-1",
                "email": "ret@example.com",
                "email_verified": True,
                "name": "Returner",
            },
        )

        response = client.get("/auth/google/callback", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"
        assert "session" in response.cookies


@pytest.mark.integration
class TestEmailMatchVerifiedAutoLinks:
    def test_verified_email_auto_links(
        self, client, db_session, seed_currencies, monkeypatch
    ):
        user = User(
            username="passworduser",
            email="linkme@example.com",
            hashed_password=hash_password("Correct-Horse-Battery-42!"),
        )
        db_session.add(user)
        db_session.flush()

        _patch_google(
            monkeypatch,
            {
                "sub": "google-link-1",
                "email": "linkme@example.com",
                "email_verified": True,
                "name": "Link Me",
            },
        )

        response = client.get("/auth/google/callback", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"

        link = db_session.scalars(
            select(UserAuthProvider).where(
                UserAuthProvider.provider == OAuthProvider.google,
                UserAuthProvider.provider_user_id == "google-link-1",
            )
        ).first()
        assert link is not None
        assert link.user_id == user.id


@pytest.mark.integration
class TestEmailMatchUnverifiedRefusesAutoLink:
    def test_unverified_match_bounces_to_login(
        self, client, db_session, seed_currencies, monkeypatch
    ):
        user = User(
            username="safeuser",
            email="safe@example.com",
            hashed_password=hash_password("Correct-Horse-Battery-42!"),
        )
        db_session.add(user)
        db_session.flush()

        _patch_google(
            monkeypatch,
            {
                "sub": "google-unverified-1",
                "email": "safe@example.com",
                "email_verified": False,
                "name": "Not Safe",
            },
        )

        response = client.get("/auth/google/callback", follow_redirects=False)
        assert response.status_code == 409
        assert "already exists" in response.text.lower()

        # No provider row should have been created.
        link = db_session.scalars(
            select(UserAuthProvider).where(
                UserAuthProvider.provider == OAuthProvider.google,
                UserAuthProvider.provider_user_id == "google-unverified-1",
            )
        ).first()
        assert link is None
