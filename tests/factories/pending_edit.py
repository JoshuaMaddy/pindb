"""PendingEditFactory — builds a PendingEdit row for chain-flow tests."""

from __future__ import annotations

import factory

from pindb.database.pending_edit import PendingEdit
from tests.factories.base import BaseFactory


class PendingEditFactory(BaseFactory):
    class Meta:
        model = PendingEdit
        sqlalchemy_session_persistence = "flush"

    entity_type = "pins"
    entity_id = 0
    patch = factory.LazyFunction(dict)
    created_by_id = None
    parent_id = None
    approved_at = None
    approved_by_id = None
    rejected_at = None
    rejected_by_id = None
