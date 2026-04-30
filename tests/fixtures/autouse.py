"""Autouse fixtures: rate limits, audit ContextVars, factory session binding."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tests.fixtures import core


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Clear in-memory rate-limit counters between tests so tests that
    share an endpoint (login, signup, password-change) do not inherit
    hits from earlier ones and trip 429 prematurely."""
    from pindb.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture(autouse=True)
def _reset_audit_context():
    """Clear the audit user ContextVars before and after each test.

    The `attach_user_middleware` sets these on every request, but direct
    db_session writes (factories, fixtures) can leave them stale.
    """
    from pindb.audit_events import set_audit_user, set_audit_user_flags

    set_audit_user(None)
    set_audit_user_flags(is_admin=False, is_editor=False)
    yield
    set_audit_user(None)
    set_audit_user_flags(is_admin=False, is_editor=False)


@pytest.fixture(autouse=True)
def bind_factories(request: pytest.FixtureRequest):
    """Wire all factory_boy factories to the current test's session."""
    if core.is_unit_or_e2e_test(request=request):
        yield
        return

    db_session: Session = request.getfixturevalue("db_session")
    try:
        import tests.factories.base as _base

        _base._current_session = db_session
        yield
        _base._current_session = None
    except ImportError:
        yield
