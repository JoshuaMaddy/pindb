"""CurrencyFactory — creates Currency rows for tests that need a specific currency."""

from __future__ import annotations

import factory

from pindb.database.currency import Currency
from tests.factories.base import BaseFactory


class CurrencyFactory(BaseFactory):
    class Meta:
        model = Currency
        sqlalchemy_session_persistence = "flush"

    id = factory.Sequence(lambda n: 900 + n)  # avoid clashing with real ISO codes
    name = factory.Sequence(lambda n: f"Test Currency {n}")
    code = factory.Sequence(lambda n: f"TC{n:01d}")


class USDCurrencyFactory(CurrencyFactory):
    """Convenience factory for the standard USD currency (id=840)."""

    id = 840
    name = "US Dollar"
    code = "USD"
