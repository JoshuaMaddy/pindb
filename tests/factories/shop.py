"""ShopFactory."""

from __future__ import annotations

from datetime import datetime, timezone

import factory

import tests.factories.base as _factory_base
from pindb.database.shop import Shop, ShopAlias
from tests.factories.base import BaseFactory


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ShopFactory(BaseFactory):
    class Meta:
        model = Shop
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Shop {n}")
    description = None
    active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        approved = kwargs.pop("approved", True)
        created_by = kwargs.pop("created_by", None)
        aliases: list[str] = kwargs.pop("aliases", []) or []
        shop = super()._create(model_class, *args, **kwargs)
        session = _factory_base._current_session
        if created_by is not None:
            shop.created_by_id = (
                created_by.id if hasattr(created_by, "id") else created_by
            )
        if approved:
            shop.approved_at = _utc_now()
        else:
            shop.approved_at = None
            shop.approved_by_id = None
        if aliases:
            shop.aliases = [ShopAlias(alias=a) for a in aliases]
        session.flush()
        return shop
