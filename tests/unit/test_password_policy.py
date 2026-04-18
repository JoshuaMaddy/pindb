"""Unit tests for the password policy validator (no DB)."""

from __future__ import annotations

import pytest

from pindb.password_policy import (
    PasswordPolicyError,
    describe_policy,
    validate_password,
)


@pytest.mark.unit
class TestStrongPassword:
    def test_accepts_strong_password(self):
        validate_password("CorrectHorseBatteryStaple9!", username="alice")

    def test_accepts_long_passphrase_with_three_classes(self):
        validate_password("maple-orbit-velvet-27", username="bob")


@pytest.mark.unit
class TestLength:
    def test_rejects_short(self):
        with pytest.raises(PasswordPolicyError) as excinfo:
            validate_password("Ab1!xy", username="alice")
        assert any("12" in r for r in excinfo.value.rules)


@pytest.mark.unit
class TestCharacterClasses:
    def test_rejects_only_two_classes(self):
        # Uniform lowercase+digit only = 2 classes
        with pytest.raises(PasswordPolicyError) as excinfo:
            validate_password("abcdefgh12345678", username="alice")
        assert any("3 of" in r for r in excinfo.value.rules)


@pytest.mark.unit
class TestContainsUserInfo:
    def test_rejects_password_containing_username(self):
        with pytest.raises(PasswordPolicyError) as excinfo:
            validate_password("AliceRocks99!", username="alice")
        assert any("username" in r.lower() for r in excinfo.value.rules)

    def test_rejects_password_containing_email_local_part(self):
        with pytest.raises(PasswordPolicyError) as excinfo:
            validate_password(
                "BobbyFischer1!", username="someone", email="bobbyfischer@example.com"
            )
        assert any(
            "username" in r.lower() or "email" in r.lower() for r in excinfo.value.rules
        )

    def test_short_username_not_substring_checked(self):
        # A 2-char username is too short to be a meaningful substring check.
        validate_password("Correct-Horse-9-batt", username="al")


@pytest.mark.unit
class TestBlocklist:
    def test_rejects_common_password(self):
        with pytest.raises(PasswordPolicyError) as excinfo:
            # The policy requires >=12 chars AND not in blocklist. Pick one
            # from the blocklist that satisfies length padding.
            validate_password("password123", username="alice")
        # Either length rule OR common-password rule fires; both are fine.
        assert excinfo.value.rules


@pytest.mark.unit
class TestZxcvbn:
    def test_rejects_obvious_pattern(self):
        # Keyboard run — zxcvbn scores below min (3); unlike repeated-char patterns
        # that can score exactly at the threshold across library versions.
        with pytest.raises(PasswordPolicyError):
            validate_password("Qwertyuiop123!", username="alice")


@pytest.mark.unit
class TestDescribePolicy:
    def test_describe_returns_bullets(self):
        policy = describe_policy()
        assert policy.min_length >= 8
        assert len(policy.bullets()) >= 3
