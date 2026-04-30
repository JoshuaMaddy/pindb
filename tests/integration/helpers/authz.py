"""Shared auth assertions for integration route tests."""

from __future__ import annotations


def assert_admin_only_get(path: str, anon_client, auth_client, editor_client) -> None:
    assert anon_client.get(path, follow_redirects=False).status_code == 401
    assert auth_client.get(path, follow_redirects=False).status_code == 403
    assert editor_client.get(path, follow_redirects=False).status_code == 403


def assert_admin_only_post(path: str, anon_client, auth_client, editor_client) -> None:
    assert anon_client.post(path, follow_redirects=False).status_code == 401
    assert auth_client.post(path, follow_redirects=False).status_code == 403
    assert editor_client.post(path, follow_redirects=False).status_code == 403


def assert_editor_or_admin_get(path: str, anon_client, auth_client) -> None:
    assert anon_client.get(path, follow_redirects=False).status_code == 401
    assert auth_client.get(path, follow_redirects=False).status_code == 403


def assert_editor_or_admin_get_loose_anon(path: str, anon_client, auth_client) -> None:
    """Guest may see 401 or 403 depending on route; regular user is 403."""
    assert anon_client.get(path, follow_redirects=False).status_code in (401, 403)
    assert auth_client.get(path, follow_redirects=False).status_code == 403


def assert_admin_only_get_loose_anon(
    path: str, anon_client, auth_client, editor_client
) -> None:
    """Like ``assert_admin_only_get`` but guest may be 401 or 403."""
    assert anon_client.get(path, follow_redirects=False).status_code in (401, 403)
    assert auth_client.get(path, follow_redirects=False).status_code == 403
    assert editor_client.get(path, follow_redirects=False).status_code == 403


def assert_admin_only_post_loose_anon(
    path: str, anon_client, auth_client, editor_client
) -> None:
    """Like ``assert_admin_only_post`` but guest may be 401 or 403."""
    assert anon_client.post(path, follow_redirects=False).status_code in (401, 403)
    assert auth_client.post(path, follow_redirects=False).status_code == 403
    assert editor_client.post(path, follow_redirects=False).status_code == 403
