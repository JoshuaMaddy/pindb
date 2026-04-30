"""Integration tests for /auth/* routes (signup, login, logout)."""

import pytest
from sqlalchemy import select

from pindb.database.user import User
from tests.fixtures.users import SUBJECT_USER_PARAMS

STRONG_PASSWORD = "Correct-Horse-Battery-42!"


@pytest.mark.integration
class TestGetLoginPage:
    def test_returns_200(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200

    def test_contains_form(self, client):
        response = client.get("/auth/login")
        assert "username" in response.text.lower() or "login" in response.text.lower()


@pytest.mark.integration
class TestGetSignupPage:
    def test_returns_200(self, client):
        response = client.get("/auth/signup")
        assert response.status_code == 200


@pytest.mark.integration
class TestPostSignup:
    def test_creates_user_and_redirects(self, client, db_session):
        response = client.post(
            "/auth/signup",
            data={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": STRONG_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/"

        user = db_session.scalars(
            select(User).where(User.username == "newuser")
        ).first()
        assert user is not None
        assert user.email == "newuser@example.com"

    def test_sets_session_cookie_on_signup(self, client):
        response = client.post(
            "/auth/signup",
            data={
                "username": "cookieuser",
                "email": "cookie@example.com",
                "password": STRONG_PASSWORD,
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "session" in response.cookies

    def test_weak_password_rejected(self, client):
        response = client.post(
            "/auth/signup",
            data={
                "username": "weakuser",
                "email": "weak@example.com",
                "password": "password",
            },
        )
        assert response.status_code == 400
        assert "password" in response.text.lower()

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_duplicate_username_returns_400(self, client, subject_user):
        response = client.post(
            "/auth/signup",
            data={
                "username": subject_user.username,
                "email": f"other-{subject_user.username}@example.com",
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == 400
        # Unified message avoids leaking whether username vs email clashed.
        assert "aren" in response.text.lower() and "available" in response.text.lower()

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_duplicate_email_returns_400(self, client, subject_user):
        response = client.post(
            "/auth/signup",
            data={
                "username": f"brandnew_{subject_user.username}",
                "email": subject_user.email,
                "password": STRONG_PASSWORD,
            },
        )
        assert response.status_code == 400
        assert "aren" in response.text.lower() and "available" in response.text.lower()


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
class TestPostLogout:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_logout_redirects(self, auth_client_as_subject, subject_user):
        response = auth_client_as_subject.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 303

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_logout_clears_session_cookie(self, auth_client_as_subject, subject_user):
        response = auth_client_as_subject.post("/auth/logout", follow_redirects=False)
        # The cookie should be deleted (empty value or expired)
        session_cookie = response.cookies.get("session")
        assert session_cookie is None or session_cookie == ""

    def test_logout_without_session_redirects(self, client):
        response = client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 303
