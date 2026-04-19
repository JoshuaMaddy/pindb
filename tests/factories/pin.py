"""PinFactory — creates Pin rows with required relationships."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import factory
from sqlalchemy import select

import tests.factories.base as _factory_base
from pindb.database.currency import Currency
from pindb.database.pin import Pin
from pindb.models.acquisition_type import AcquisitionType
from tests.factories.base import BaseFactory


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PinFactory(BaseFactory):
    class Meta:
        model = Pin
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Pin {n}")
    acquisition_type = AcquisitionType.single
    front_image_guid = factory.LazyFunction(uuid.uuid4)

    # Control params (not model fields) — set approved=False for a pending pin
    class Params:
        approved = True
        created_by = None

    @factory.lazy_attribute
    def currency(self):
        """
        Return an existing currency (seed_currencies populates these), or create
        a test-only one if none exist yet.

        Must access _factory_base._current_session via the module reference, not a
        direct import — the `from module import var` binding captures the value at
        import time (None), and won't see updates made by the bind_factories fixture.
        """
        session = _factory_base._current_session
        existing = session.scalars(select(Currency).limit(1)).first()
        if existing is not None:
            return existing
        c = Currency(id=900, name="Test Currency", code="TST")
        session.add(c)
        session.flush()
        return c

    # Relationship defaults — empty sets (no grades/shops/artists unless specified)
    grades = factory.LazyFunction(set)
    shops = factory.LazyFunction(set)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        approved = kwargs.pop("approved", True)
        created_by = kwargs.pop("created_by", None)
        pin = super()._create(model_class, *args, **kwargs)
        session = _factory_base._current_session
        # Override audit/pending fields post-create (they have init=False).
        if created_by is not None:
            pin.created_by_id = (
                created_by.id if hasattr(created_by, "id") else created_by
            )
        if approved:
            pin.approved_at = _utc_now()
        else:
            pin.approved_at = None
            pin.approved_by_id = None
        session.flush()
        return pin
