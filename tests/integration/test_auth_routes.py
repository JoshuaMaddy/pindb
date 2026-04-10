"""Integration tests for /auth/* routes (signup, login, logout)."""

import pytest
from sqlalchemy import select

from pindb.database.user import User


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
                "password": "password123",
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
                "password": "pass",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "session" in response.cookies

    def test_duplicate_username_returns_400(self, client, test_user):
        response = client.post(
            "/auth/signup",
            data={
                "username": "testuser",  # already exists via test_user fixture
                "email": "other@example.com",
                "password": "pass",
            },
        )
        assert response.status_code == 400
        assert "already taken" in response.text.lower()

    def test_duplicate_email_returns_400(self, client, test_user):
        response = client.post(
            "/auth/signup",
            data={
                "username": "brandnewuser",
                "email": "test@example.com",  # already exists via test_user fixture
                "password": "pass",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.text.lower()


@pytest.mark.integration
class TestPostLogin:
    def test_correct_credentials_redirects(self, client, test_user):
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpassword"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/"

    def test_correct_credentials_sets_cookie(self, client, test_user):
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpassword"},
            follow_redirects=False,
        )
        assert "session" in response.cookies

    def test_wrong_password_returns_401(self, client, test_user):
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
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
    def test_logout_redirects(self, auth_client):
        response = auth_client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 303

    def test_logout_clears_session_cookie(self, auth_client):
        response = auth_client.post("/auth/logout", follow_redirects=False)
        # The cookie should be deleted (empty value or expired)
        session_cookie = response.cookies.get("session")
        assert session_cookie is None or session_cookie == ""

    def test_logout_without_session_redirects(self, client):
        response = client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 303
