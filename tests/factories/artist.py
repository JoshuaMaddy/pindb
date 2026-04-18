"""ArtistFactory."""

from __future__ import annotations

from datetime import datetime, timezone

import factory
import tests.factories.base as _factory_base

from pindb.database.artist import Artist
from tests.factories.base import BaseFactory


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ArtistFactory(BaseFactory):
    class Meta:
        model = Artist
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Artist {n}")
    description = None
    active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        approved = kwargs.pop("approved", True)
        created_by = kwargs.pop("created_by", None)
        artist = super()._create(model_class, *args, **kwargs)
        session = _factory_base._current_session
        if created_by is not None:
            artist.created_by_id = (
                created_by.id if hasattr(created_by, "id") else created_by
            )
        if approved:
            artist.approved_at = _utc_now()
        else:
            artist.approved_at = None
            artist.approved_by_id = None
        session.flush()
        return artist
