"""PinFactory — creates Pin rows with required relationships."""

from __future__ import annotations

import uuid

import factory
import tests.factories.base as _factory_base
from sqlalchemy import select

from pindb.database.currency import Currency
from pindb.database.pin import Pin
from pindb.models.acquisition_type import AcquisitionType
from tests.factories.base import BaseFactory


class PinFactory(BaseFactory):
    class Meta:
        model = Pin
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Pin {n}")
    acquisition_type = AcquisitionType.single
    front_image_guid = factory.LazyFunction(uuid.uuid4)

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
    materials = factory.LazyFunction(set)
    shops = factory.LazyFunction(set)
