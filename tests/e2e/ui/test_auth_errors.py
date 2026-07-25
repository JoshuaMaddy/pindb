"""Login error rendering."""

from __future__ import annotations

from tests.e2e.ui.http import parse_html as _soup


class TestAuthErrorMessages:
    def test_invalid_login_renders_error_message(self, anon_http_client):
        response = anon_http_client.post(
            "/auth/login",
            data={"username": "nope_no_user_here", "password": "wrongpass"},
        )
        assert response.status_code == 401
        soup = _soup(response)
        assert "Invalid username or password." in soup.get_text()
        headings = [h.get_text(strip=True) for h in soup.select("h1")]
        assert "Login" in headings
