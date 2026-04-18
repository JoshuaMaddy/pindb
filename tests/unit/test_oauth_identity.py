"""Unit tests for OAuth identity normalisation (no DB / no network)."""

from __future__ import annotations

import pytest

from pindb.database.user_auth_provider import OAuthProvider
from pindb.routes.auth._oauth import (
    normalize_discord,
    normalize_google,
    normalize_meta,
)


@pytest.mark.unit
class TestNormalizeGoogle:
    def test_verified_email(self):
        identity = normalize_google(
            {
                "sub": "112233",
                "email": "alice@example.com",
                "email_verified": True,
                "name": "Alice A",
            }
        )
        assert identity.provider is OAuthProvider.google
        assert identity.provider_user_id == "112233"
        assert identity.email == "alice@example.com"
        assert identity.email_verified is True
        assert identity.username_hint == "Alice A"

    def test_missing_name_falls_back_to_email_local(self):
        identity = normalize_google(
            {"sub": "1", "email": "bob@x.test", "email_verified": True}
        )
        assert identity.username_hint == "bob"

    def test_unverified_email(self):
        identity = normalize_google(
            {"sub": "1", "email": "x@x.test", "email_verified": False, "name": "X"}
        )
        assert identity.email_verified is False


@pytest.mark.unit
class TestNormalizeDiscord:
    def test_verified_email(self):
        identity = normalize_discord(
            {
                "id": "u1",
                "username": "cooluser",
                "global_name": "Cool User",
                "email": "cool@x.test",
                "verified": True,
            }
        )
        assert identity.provider is OAuthProvider.discord
        assert identity.provider_user_id == "u1"
        assert identity.email_verified is True
        assert identity.username_hint == "Cool User"
        assert identity.provider_username == "cooluser"

    def test_unverified_email(self):
        identity = normalize_discord(
            {"id": "u2", "username": "x", "email": "x@x.test", "verified": False}
        )
        assert identity.email_verified is False

    def test_no_email(self):
        identity = normalize_discord({"id": "u3", "username": "y"})
        assert identity.email is None
        assert identity.email_verified is False


@pytest.mark.unit
class TestNormalizeMeta:
    def test_with_email_is_verified(self):
        identity = normalize_meta(
            {"id": "m1", "name": "Meta Person", "email": "meta@x.test"}
        )
        assert identity.provider is OAuthProvider.meta
        assert identity.email == "meta@x.test"
        assert identity.email_verified is True
        assert identity.username_hint == "Meta Person"

    def test_without_email_is_unverified(self):
        identity = normalize_meta({"id": "m2", "name": "No Email"})
        assert identity.email is None
        assert identity.email_verified is False
        assert identity.username_hint == "No Email"
