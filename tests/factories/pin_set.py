"""PinSetFactory — global (curator) and personal (user-owned) variants."""

from __future__ import annotations

from datetime import datetime, timezone

import factory

import tests.factories.base as _factory_base
from pindb.database.pin_set import PinSet
from tests.factories.base import BaseFactory


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PinSetFactory(BaseFactory):
    class Meta:
        model = PinSet
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Set {n}")
    description = None
    owner_id = None  # None = global/curator set

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        approved = kwargs.pop("approved", True)
        created_by = kwargs.pop("created_by", None)
        pin_set = super()._create(model_class, *args, **kwargs)
        session = _factory_base._current_session
        if created_by is not None:
            pin_set.created_by_id = (
                created_by.id if hasattr(created_by, "id") else created_by
            )
        if approved:
            pin_set.approved_at = _utc_now()
        else:
            pin_set.approved_at = None
            pin_set.approved_by_id = None
        session.flush()
        return pin_set


class PersonalPinSetFactory(PinSetFactory):
    """A user-owned personal pin set. Pass owner_id=user.id when creating."""

    owner_id = None  # caller must supply: PersonalPinSetFactory(owner_id=user.id)
