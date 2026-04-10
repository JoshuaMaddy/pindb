"""TagFactory."""

from __future__ import annotations

import factory

from pindb.database.tag import Tag
from tests.factories.base import BaseFactory


class TagFactory(BaseFactory):
    class Meta:
        model = Tag
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"test-tag-{n}")
    parent_id = None
