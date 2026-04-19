"""TagFactory."""

from __future__ import annotations

from datetime import datetime, timezone

import factory

import tests.factories.base as _factory_base
from pindb.database.tag import Tag, TagAlias, TagCategory
from tests.factories.base import BaseFactory


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TagFactory(BaseFactory):
    class Meta:
        model = Tag
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"test-tag-{n}")
    category = TagCategory.general

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        approved = kwargs.pop("approved", True)
        created_by = kwargs.pop("created_by", None)
        aliases: list[str] = kwargs.pop("aliases", []) or []
        tag = super()._create(model_class, *args, **kwargs)
        session = _factory_base._current_session
        if created_by is not None:
            tag.created_by_id = (
                created_by.id if hasattr(created_by, "id") else created_by
            )
        if approved:
            tag.approved_at = _utc_now()
        else:
            tag.approved_at = None
            tag.approved_by_id = None
        if aliases:
            tag.aliases = [TagAlias(alias=a) for a in aliases]
        session.flush()
        return tag
