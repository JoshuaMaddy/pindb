"""Rich message body variants, serialized as a discriminated union on ``type``.

The union is stored in ``Message.body`` via
:class:`pindb.database.types.PydanticJSON`. New render kinds are added by
appending a variant with a fresh ``type`` literal, with no schema migration
required — the column is plain JSONB.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter


class TextBody(BaseModel):
    """Plain text / markdown message."""

    type: Literal["text"] = "text"
    text: str


class PinRejectionBody(BaseModel):
    """Explains why a pending pin submission or edit was rejected.

    The canonical entity reference lives on the ``Message`` row
    (``related_entity_type`` / ``related_entity_id``); ``pin_id`` here is a
    convenience echo for rendering.
    """

    type: Literal["pin_rejection"] = "pin_rejection"
    reason: str
    pin_id: int | None = None


class ContributionBody(BaseModel):
    """Acknowledges or records a user contribution."""

    type: Literal["contribution"] = "contribution"
    summary: str
    points: int | None = None


MessageBody = Annotated[
    Union[TextBody, PinRejectionBody, ContributionBody],
    Field(discriminator="type"),
]

MessageBodyAdapter: TypeAdapter[MessageBody] = TypeAdapter(MessageBody)
