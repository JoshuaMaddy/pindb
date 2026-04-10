"""ShopFactory."""

from __future__ import annotations

import factory

from pindb.database.shop import Shop
from tests.factories.base import BaseFactory


class ShopFactory(BaseFactory):
    class Meta:
        model = Shop
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Shop {n}")
    description = None
    active = True
