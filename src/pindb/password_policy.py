"""Password strength policy for signup and password change.

Enforces (in order of severity):
  * Minimum length (``CONFIGURATION.password_min_length``, default 12).
  * At least 3 of 4 character classes: lower, upper, digit, symbol.
  * The password may not contain the user's username or email local-part.
  * A small inline blocklist of notoriously common passwords.
  * A minimum zxcvbn score (default 3) — zxcvbn ships its own 30k+ word
    dictionary, which covers most real-world leaked/common passwords.

Existing users' hashed passwords are not re-validated; only new passwords
submitted to ``/auth/signup`` or ``/user/me/password`` flow through here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from zxcvbn import zxcvbn

from pindb.config import CONFIGURATION

# A small inline blocklist so we reject the top offenders even when zxcvbn
# happens to score them above the threshold for short inputs. zxcvbn's own
# dictionaries cover far more; this is belt-and-braces.
_COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "password1",
        "password123",
        "passw0rd",
        "p@ssw0rd",
        "qwerty",
        "qwerty123",
        "123456",
        "12345678",
        "123456789",
        "1234567890",
        "letmein",
        "welcome",
        "welcome1",
        "admin",
        "administrator",
        "iloveyou",
        "monkey",
        "dragon",
        "sunshine",
        "princess",
        "football",
        "baseball",
        "master",
        "michael",
        "shadow",
        "abc123",
        "trustno1",
        "changeme",
        "pindb",
    }
)


class PasswordPolicyError(ValueError):
    """Raised when a password fails one or more policy rules.

    ``rules`` holds human-readable messages for each unmet rule, in the
    same order they were checked. UI surfaces can render them as a list.
    """

    def __init__(self, rules: list[str]) -> None:
        super().__init__("; ".join(rules))
        self.rules = rules


@dataclass(frozen=True, slots=True)
class PolicyDescription:
    """Machine-readable description of the currently configured rules.

    Useful for rendering inline hints on the signup / change-password pages.
    """

    min_length: int
    min_character_classes: int = 3
    min_zxcvbn_score: int = field(default=3)

    def bullets(self) -> list[str]:
        """Return human-readable bullet strings describing the active policy."""
        return [
            f"At least {self.min_length} characters.",
            "Mix at least 3 of: lowercase, uppercase, digits, symbols.",
            "Must not contain your username or email.",
            "Must not be a common / obvious password.",
        ]


def describe_policy() -> PolicyDescription:
    """Return the password policy limits from ``CONFIGURATION`` for UI hints.

    Returns:
        PolicyDescription: Minimum length, class count, and zxcvbn floor
            currently in effect.
    """
    return PolicyDescription(
        min_length=CONFIGURATION.password_min_length,
        min_character_classes=3,
        min_zxcvbn_score=CONFIGURATION.password_min_zxcvbn_score,
    )


def _character_classes(password: str) -> int:
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    return sum((has_lower, has_upper, has_digit, has_symbol))


def _contains_user_info(
    password: str, *, username: str | None, email: str | None
) -> bool:
    lowered = password.lower()
    candidates: list[str] = []
    if username:
        candidates.append(username.lower())
    if email:
        local = email.split("@", 1)[0].lower()
        if local:
            candidates.append(local)
    return any(
        candidate and len(candidate) >= 3 and candidate in lowered
        for candidate in candidates
    )


def validate_password(
    password: str,
    *,
    username: str | None = None,
    email: str | None = None,
) -> None:
    """Validate *password* against length, complexity, blocklist, and zxcvbn score.

    Args:
        password (str): Candidate password (caller trims whitespace if desired).
        username (str | None): Substrings from this value must not appear in
            *password* (case-insensitive) when length ≥ 3.
        email (str | None): Same for the email local-part before ``@``.

    Raises:
        PasswordPolicyError: When one or more rules fail; ``.rules`` lists
            human-readable messages in check order.
    """
    rules: list[str] = []

    min_length = CONFIGURATION.password_min_length
    if len(password) < min_length:
        rules.append(f"Password must be at least {min_length} characters.")

    if _character_classes(password) < 3:
        rules.append(
            "Password must include at least 3 of: lowercase, uppercase, "
            "digits, symbols."
        )

    if _contains_user_info(password, username=username, email=email):
        rules.append("Password must not contain your username or email.")

    if password.lower() in _COMMON_PASSWORDS:
        rules.append("Password is too common; pick something less obvious.")

    user_inputs: list[str] = [v for v in (username, email) if v]
    try:
        result = zxcvbn(password, user_inputs=user_inputs)
        score = int(result.get("score", 0))
    except Exception:
        # zxcvbn should not fail for normal inputs, but don't let a bug
        # in the library lock users out; treat it as "no extra info".
        score = 4

    min_score = CONFIGURATION.password_min_zxcvbn_score
    if score < min_score:
        rules.append(
            "Password is too easy to guess; try a longer passphrase or "
            "add uncommon words."
        )

    if rules:
        raise PasswordPolicyError(rules)


def iter_blocklist() -> Iterable[str]:
    """Yield passwords in the small inline blocklist.

    Returns:
        Iterable[str]: Iterator over ``_COMMON_PASSWORDS`` (mainly for tests).
    """
    return iter(_COMMON_PASSWORDS)
