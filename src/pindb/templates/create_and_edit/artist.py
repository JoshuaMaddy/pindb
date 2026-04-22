"""
htpy page and fragment builders: `templates/create_and_edit/artist.py`.
"""

from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element

from pindb.database.artist import Artist
from pindb.templates.create_and_edit._simple_aliased_entity import (
    simple_aliased_entity_form,
)


def artist_form(
    post_url: URL | str,
    request: Request,
    artist: Artist | None = None,
) -> Element:
    return simple_aliased_entity_form(
        post_url=post_url,
        request=request,
        entity=artist,
        entity_kind="Artist",
        create_icon="palette",
        create_article="an",
    )
