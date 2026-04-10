"""
Integration-level conftest.

Makes seed_currencies autouse for the entire integration suite so every test
starts with currencies in the DB (required by Pin and many routes).
"""

import pytest


@pytest.fixture(autouse=True)
def currencies(seed_currencies):
    """Ensure ISO currencies are present for every integration test."""
    pass
