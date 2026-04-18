"""Integration tests for password policy on signup + password change."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.auth import verify_password
from pindb.database.user import User

STRONG = "Correct-Horse-Battery-42!"
ALSO_STRONG = "Velvet-Orbit-Maple-91!"


@pytest.mark.integration
class TestSignupPolicy:
    def test_weak_password_rejected_with_rules(self, client):
        response = client.post(
            "/auth/signup",
            data={
                "username": "weakie",
                "email": "w@example.com",
                "password": "short1",
            },
        )
        assert response.status_code == 400
        assert "password" in response.text.lower()

    def test_strong_password_accepted(self, client):
        response = client.post(
            "/auth/signup",
            data={
                "username": "stronger",
                "email": "strong@example.com",
                "password": STRONG,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


@pytest.mark.integration
class TestChangePassword:
    def test_happy_path(self, auth_client, test_user, db_session):
        response = auth_client.post(
            "/user/me/password",
            data={
                "current_password": "testpassword",
                "new_password": ALSO_STRONG,
                "confirm_password": ALSO_STRONG,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        user = db_session.scalars(select(User).where(User.id == test_user.id)).first()
        assert user is not None
        assert user.hashed_password is not None
        assert verify_password(ALSO_STRONG, user.hashed_password)

    def test_wrong_current_password(self, auth_client):
        response = auth_client.post(
            "/user/me/password",
            data={
                "current_password": "wrong-current",
                "new_password": ALSO_STRONG,
                "confirm_password": ALSO_STRONG,
            },
        )
        assert response.status_code == 400
        assert "current password" in response.text.lower()

    def test_weak_new_password(self, auth_client):
        response = auth_client.post(
            "/user/me/password",
            data={
                "current_password": "testpassword",
                "new_password": "short",
                "confirm_password": "short",
            },
        )
        assert response.status_code == 400
        assert "password" in response.text.lower()

    def test_mismatched_confirmation(self, auth_client):
        response = auth_client.post(
            "/user/me/password",
            data={
                "current_password": "testpassword",
                "new_password": STRONG,
                "confirm_password": ALSO_STRONG,
            },
        )
        assert response.status_code == 400
        assert "do not match" in response.text.lower()


@pytest.mark.integration
class TestOAuthOnlyUserCanSetPassword:
    def test_oauth_only_user_can_add_password_without_current(
        self, client, db_session, seed_currencies
    ):
        """An OAuth-only user has no ``hashed_password``; they should be
        able to set one without a ``current_password``."""
        import secrets
        from datetime import datetime, timedelta, timezone

        from pindb.database.session import UserSession

        user = User(username="noauth", email="noauth@example.com")
        db_session.add(user)
        db_session.flush()
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
        response = client.post(
            "/user/me/password",
            data={
                "new_password": STRONG,
                "confirm_password": STRONG,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.scalars(select(User).where(User.id == user.id)).first()
        assert refreshed is not None
        assert refreshed.hashed_password is not None
