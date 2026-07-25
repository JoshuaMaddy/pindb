"""Integration tests for /auth/* routes (login, logout) and account creation.

Signup and OAuth are gone: accounts exist only because an admin created one at
``/admin/users``. These tests pin that down, including that the removed routes
are actually unroutable rather than merely unlinked.
"""

import pytest
from sqlalchemy import select

from pindb.database.user import User
from tests.fixtures.users import SUBJECT_USER_PARAMS
from tests.integration.helpers.authz import assert_admin_only_post

STRONG_PASSWORD = "Correct-Horse-Battery-42!"


@pytest.mark.integration
class TestGetLoginPage:
    def test_returns_200(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200

    def test_contains_form(self, client):
        response = client.get("/auth/login")
        assert "username" in response.text.lower() or "login" in response.text.lower()

    def test_offers_no_signup_or_oauth(self, client):
        body = client.get("/auth/login").text.lower()
        assert "sign up" not in body
        assert "/auth/signup" not in body
        for provider in ("google", "discord", "meta"):
            assert f"/auth/{provider}" not in body

    def test_navbar_carries_only_the_wordmark(self, client):
        """Every other nav destination 401s for a guest, so none are offered."""
        body = client.get("/auth/login").text
        assert ">PinDB<" in body
        for href in ('href="/list"', 'href="/search/pin"', 'href="/create"'):
            assert href not in body
        assert 'href="/auth/login"' not in body

    def test_signed_in_member_still_gets_the_nav_links(self, auth_client):
        """The logged-out stripping must not reach a plain member's navbar."""
        body = auth_client.get("/").text
        assert 'href="/list"' in body
        assert 'href="/search/pin"' in body


@pytest.mark.integration
class TestRemovedAuthRoutes:
    @pytest.mark.parametrize(
        "path",
        [
            "/auth/signup",
            "/auth/google",
            "/auth/discord",
            "/auth/meta",
            "/auth/google/callback",
            "/auth/oauth/onboarding",
        ],
    )
    def test_get_is_not_routable(self, anon_client, auth_client, path):
        # A guest gets 401 from the gate, which runs before routing — removed
        # paths are indistinguishable from private ones, so nothing here is an
        # existence oracle. A member gets the real answer: gone.
        assert anon_client.get(path, follow_redirects=False).status_code == 401
        assert auth_client.get(path, follow_redirects=False).status_code == 404

    def test_signup_post_is_not_routable(self, auth_client):
        response = auth_client.post(
            "/auth/signup",
            data={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": STRONG_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestPostLogin:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_correct_credentials_redirects(self, client, subject_user):
        response = client.post(
            "/auth/login",
            data={"username": subject_user.username, "password": "testpassword"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/"

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_correct_credentials_sets_cookie(self, client, subject_user):
        response = client.post(
            "/auth/login",
            data={"username": subject_user.username, "password": "testpassword"},
            follow_redirects=False,
        )
        assert "session" in response.cookies

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_wrong_password_returns_401(self, client, subject_user):
        response = client.post(
            "/auth/login",
            data={
                "username": subject_user.username,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_unknown_username_returns_401(self, client):
        response = client.post(
            "/auth/login",
            data={"username": "ghost", "password": "whatever"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestLoginNextTarget:
    """``next`` sends a member back to where the gate interrupted them."""

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_relative_next_is_honoured(self, client, subject_user):
        response = client.post(
            "/auth/login",
            data={
                "username": subject_user.username,
                "password": "testpassword",
                "next": "/list/tags?page=2",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/list/tags?page=2"

    @pytest.mark.parametrize(
        "hostile",
        [
            "https://evil.example/steal",
            "//evil.example/steal",
            "/\\evil.example",
            "http://evil.example",
            "not-a-path",
        ],
    )
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_offsite_next_is_ignored(self, client, subject_user, hostile):
        response = client.post(
            "/auth/login",
            data={
                "username": subject_user.username,
                "password": "testpassword",
                "next": hostile,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/"


@pytest.mark.integration
class TestPostLogout:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_logout_redirects_to_login(self, auth_client_as_subject, subject_user):
        response = auth_client_as_subject.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/auth/login"

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_logout_clears_session_cookie(self, auth_client_as_subject, subject_user):
        response = auth_client_as_subject.post("/auth/logout", follow_redirects=False)
        # The cookie should be deleted (empty value or expired)
        session_cookie = response.cookies.get("session")
        assert session_cookie is None or session_cookie == ""

    def test_logout_without_session_redirects(self, client):
        response = client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 303


@pytest.mark.integration
class TestAdminCreateUser:
    def test_admin_creates_user_who_can_log_in(self, admin_client, client, db_session):
        response = admin_client.post(
            "/admin/users/create",
            data={
                "username": "recruit",
                "email": "recruit@example.com",
                "password": STRONG_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        created = db_session.scalars(
            select(User).where(User.username == "recruit")
        ).first()
        assert created is not None
        assert created.is_admin is False
        assert created.is_editor is False

        login = client.post(
            "/auth/login",
            data={"username": "recruit", "password": STRONG_PASSWORD},
            follow_redirects=False,
        )
        assert login.status_code == 303

    def test_roles_are_applied(self, admin_client, db_session):
        admin_client.post(
            "/admin/users/create",
            data={
                "username": "editor_recruit",
                "email": "editor_recruit@example.com",
                "password": STRONG_PASSWORD,
                "is_editor": "true",
            },
            follow_redirects=False,
        )
        created = db_session.scalars(
            select(User).where(User.username == "editor_recruit")
        ).first()
        assert created is not None
        assert created.is_editor is True
        assert created.is_admin is False

    def test_weak_password_rejected(self, admin_client):
        response = admin_client.post(
            "/admin/users/create",
            data={
                "username": "weakling",
                "email": "weak@example.com",
                "password": "password",
            },
        )
        assert response.status_code == 400
        assert "password" in response.text.lower()

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_duplicate_username_rejected(self, admin_client, subject_user):
        response = admin_client.post(
            "/admin/users/create",
            data={
                "username": subject_user.username,
                "email": f"other-{subject_user.username}@example.com",
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == 400
        assert "already taken" in response.text.lower()

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_duplicate_email_rejected(self, admin_client, subject_user):
        response = admin_client.post(
            "/admin/users/create",
            data={
                "username": f"brandnew_{subject_user.username}",
                "email": subject_user.email,
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.text.lower()

    def test_requires_admin(self, anon_client, auth_client, editor_client):
        assert_admin_only_post(
            "/admin/users/create", anon_client, auth_client, editor_client
        )
