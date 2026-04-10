"""ArtistFactory."""

from __future__ import annotations

import factory

from pindb.database.artist import Artist
from tests.factories.base import BaseFactory


class ArtistFactory(BaseFactory):
    class Meta:
        model = Artist
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Test Artist {n}")
    description = None
    active = True
