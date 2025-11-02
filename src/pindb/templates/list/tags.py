from typing import Sequence

from fastapi import Request
from htpy import Element, a

from pindb.database.tag import Tag
from pindb.templates.list.base import base_list


def tags_list(request: Request, tags: Sequence[Tag]) -> Element:
    return base_list(
        title="Tags",
        items=[
            a(href=str(request.url_for("get_tag", id=tag.id)))[tag.name] for tag in tags
        ],
    )
