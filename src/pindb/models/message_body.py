"""Rich message body variants, serialized as a discriminated union on ``type``.

The union is stored in ``Message.body`` via
:class:`pindb.database.types.PydanticJSON`. New render kinds are added by
appending a variant with a fresh ``type`` literal, with no schema migration
required — the column is plain JSONB.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

from pindb.database.entity_type import EntityType


class MessageBodyBase(BaseModel):
    """Fields shared by every body variant.

    ``redirect_url`` lets a message opt into click-through navigation to an
    arbitrary in-app URL. When unset, the click target falls back to the
    ``Message`` row's ``related_entity_*`` (see ``message_target_url``), and
    failing that the message expands inline. Absent from the stored JSON means
    ``None`` — no migration needed for existing rows.
    """

    redirect_url: str | None = None


class TextBody(MessageBodyBase):
    """Plain text / markdown message."""

    type: Literal["text"] = "text"
    text: str


class ChangesRequestedBody(MessageBodyBase):
    """A reviewer's request for changes to a pending submission or edit.

    The canonical entity reference lives on the ``Message`` row
    (``related_entity_type`` / ``related_entity_id``); ``entity_type`` and
    ``entity_name`` here are convenience echoes for rendering the title without a
    DB roundtrip, and ``pin_id`` is a legacy echo kept for rows written before the
    flow covered every entity type.

    The ``type`` discriminator likewise stays ``"pin_rejection"``: it is the value
    already on disk, and a container running the previous release would fail to
    validate an unrecognized one during the blue/green overlap.
    """

    type: Literal["pin_rejection"] = "pin_rejection"
    reason: str
    entity_type: EntityType | None = None
    entity_name: str | None = None
    is_edit: bool = False
    pin_id: int | None = None


class ContributionBody(MessageBodyBase):
    """Acknowledges or records a user contribution."""

    type: Literal["contribution"] = "contribution"
    summary: str
    points: int | None = None


class AchievementBody(MessageBodyBase):
    """Announces a newly earned achievement tier."""

    type: Literal["achievement"] = "achievement"
    family: str
    tier: int
    name: str
    threshold: int
    unit_label: str


MessageBody = Annotated[
    Union[TextBody, ChangesRequestedBody, ContributionBody, AchievementBody],
    Field(discriminator="type"),
]

MessageBodyAdapter: TypeAdapter[MessageBody] = TypeAdapter(MessageBody)
