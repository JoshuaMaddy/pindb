"""PinSetFactory — global (curator) and personal (user-owned) variants."""

from __future__ import annotations

import factory

from pindb.database.pin_set import PinSet
from tests.factories.base import BaseFactory


class PinSetFactory(BaseFactory):
    class Meta:
        model = PinSet
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Set {n}")
    description = None
    owner_id = None  # None = global/curator set


class PersonalPinSetFactory(PinSetFactory):
    """A user-owned personal pin set. Pass owner_id=user.id when creating."""

    owner_id = None  # caller must supply: PersonalPinSetFactory(owner_id=user.id)
