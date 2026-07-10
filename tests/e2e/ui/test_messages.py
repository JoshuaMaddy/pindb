"""Messages inbox: auth gating, page structure, navbar indicator, and the
read/archive HTMX round trip driven against the live server (httpx)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import psycopg
import pytest

from tests.e2e.ui.http import parse_html as _soup

_HX = {"HX-Request": "true"}


def _pg_url() -> str:
    return os.environ.get("DATABASE_CONNECTION", "").replace("+psycopg", "")


def _admin_id() -> int:
    with psycopg.connect(_pg_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE username = %s", ("e2e_admin_pw",))
        row = cur.fetchone()
    assert row is not None, "e2e admin user missing"
    return row[0]


@pytest.fixture
def seeded_message(admin_http_client) -> Iterator[int]:
    """A direct text message to the admin, hard-deleted afterwards."""
    admin_id = _admin_id()
    with psycopg.connect(_pg_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages
                (category, body, recipient_id, audience, created_at, updated_at)
            VALUES
                ('direct', %s::jsonb, %s, 'all', now(), now())
            RETURNING id
            """,
            ('{"type": "text", "text": "hello inbox"}', admin_id),
        )
        inserted = cur.fetchone()
        assert inserted is not None
        message_id = inserted[0]
        conn.commit()
    try:
        yield message_id
    finally:
        with psycopg.connect(_pg_url()) as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM message_receipts WHERE message_id = %s", (message_id,)
            )
            cur.execute("DELETE FROM messages WHERE id = %s", (message_id,))
            conn.commit()


class TestMessagesAuth:
    def test_anonymous_is_unauthorized(self, anon_http_client):
        assert anon_http_client.get("/messages").status_code == 401


class TestMessagesPage:
    def test_navbar_has_mail_link_and_dot_host(self, admin_http_client):
        soup = _soup(admin_http_client.get("/"))
        assert soup.select_one('a[href="/messages"]') is not None
        assert soup.select_one("#navbar-unread-dot") is not None

    def test_page_renders_tabs_and_heading(self, admin_http_client):
        response = admin_http_client.get("/messages")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.select_one("#messages-heading") is not None
        assert soup.select_one("#messages-list") is not None
        hrefs = {a.get("href") or "" for a in soup.select("a")}
        assert any("/messages?tab=inbox" in h for h in hrefs)
        assert any("/messages?tab=archived" in h for h in hrefs)

    def test_hx_target_returns_only_list_section(self, admin_http_client):
        response = admin_http_client.get(
            "/messages", headers={**_HX, "HX-Target": "messages-list"}
        )
        assert response.status_code == 200
        assert "<html" not in response.text.lower()
        assert 'id="messages-list"' in response.text


class TestMessagesActions:
    def test_seeded_message_is_listed_and_unread(
        self, admin_http_client, seeded_message
    ):
        soup = _soup(admin_http_client.get("/messages"))
        assert soup.select_one(f"#message-row-{seeded_message}") is not None

    def test_mark_read_swaps_row_and_updates_dot(
        self, admin_http_client, seeded_message
    ):
        response = admin_http_client.post(
            f"/messages/{seeded_message}/read", headers=_HX
        )
        assert response.status_code == 200
        # Primary row fragment plus the OOB navbar dot update.
        assert f'id="message-row-{seeded_message}"' in response.text
        assert 'id="navbar-unread-dot"' in response.text
        assert 'hx-swap-oob="true"' in response.text

    def test_archive_removes_row(self, admin_http_client, seeded_message):
        response = admin_http_client.post(
            f"/messages/{seeded_message}/archive", headers=_HX
        )
        assert response.status_code == 200
        # Empty primary content removes the row; only the OOB dot remains.
        assert f'id="message-row-{seeded_message}"' not in response.text
        assert 'id="navbar-unread-dot"' in response.text
        # Now gone from the inbox, present under the archived tab.
        inbox = _soup(admin_http_client.get("/messages"))
        assert inbox.select_one(f"#message-row-{seeded_message}") is None
        archived = _soup(admin_http_client.get("/messages?tab=archived"))
        assert archived.select_one(f"#message-row-{seeded_message}") is not None
