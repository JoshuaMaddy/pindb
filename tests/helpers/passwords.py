"""Cached argon2 hashing for test fixtures.

Argon2 with production parameters costs ~100ms+ per hash, and the user fixtures
hash the same constant passwords in nearly every integration test. Caching by
plaintext turns that into one hash per password per worker; ``verify_password``
still accepts the cached hash, so login-flow tests are unaffected.

Only for fixture/factory seed data — tests exercising the hashing itself
(``tests/unit/test_auth_helpers.py``) must keep calling ``hash_password``.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=None)
def hashed(password: str) -> str:
    from pindb.auth import hash_password

    return hash_password(password)
