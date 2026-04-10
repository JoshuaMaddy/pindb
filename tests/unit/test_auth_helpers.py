"""Unit tests for password hashing helpers in src/pindb/auth.py — no DB required."""

import pytest

from pindb.auth import hash_password, verify_password


@pytest.mark.unit
class TestHashPassword:
    def test_returns_string(self):
        result = hash_password("mysecret")
        assert isinstance(result, str)

    def test_not_plaintext(self):
        result = hash_password("mysecret")
        assert result != "mysecret"

    def test_different_hashes_for_same_password(self):
        # Argon2 uses random salts, so two hashes of the same password differ
        h1 = hash_password("mysecret")
        h2 = hash_password("mysecret")
        assert h1 != h2


@pytest.mark.unit
class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_wrong(self):
        hashed = hash_password("correctpassword")
        assert verify_password("", hashed) is False

    def test_round_trip_various_passwords(self):
        passwords = ["abc", "a" * 100, "p@$$w0rd!", "unicode-こんにちは"]
        for pw in passwords:
            assert verify_password(pw, hash_password(pw)) is True
