"""User "Display" pages: photos of a collector's real-life pin display.

A :class:`UserDisplay` is a 1:1 container row per user (created lazily on first
visit to the editor, not at signup — otherwise every account that never uses the
feature leaves an empty row behind). It holds the presentation choices; the
photos themselves are :class:`UserDisplayImage` rows ordered by ``position``.

**The cover photo is the image at the lowest ``position``.** There is
deliberately no ``cover_image_id`` column: it would create a circular foreign key
between the two tables and would need a fixup every time the cover is deleted.
"Drag your best photo first" is a gesture the editor already supports, and the
Open Graph card reads position 0.
"""

from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from rich.repr import Result
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy import (
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    object_session,
    relationship,
)

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.joins import display_image_pins

if TYPE_CHECKING:
    from pindb.database.pin import Pin
    from pindb.database.user import User


class DisplayLayout(StrEnum):
    """How a display page arranges its photos."""

    collage = auto()
    grid = auto()
    vertical = auto()
    carousel = auto()


class DisplayImageSize(StrEnum):
    """Per-photo size hint. ``feature`` spans two columns in collage/grid."""

    normal = auto()
    feature = auto()


# A display is a personal page, not a catalog: the cap exists to keep the page
# renderable and the OG card cheap, not to ration storage.
MAX_DISPLAY_IMAGES: int = 30

MAX_TITLE_LENGTH: int = 120
MAX_BLURB_LENGTH: int = 300
MAX_CAPTION_LENGTH: int = 200

# Every enum column below is declared with this explicit length. Without it,
# ``native_enum=False`` sizes the VARCHAR to the longest value that exists *at
# migration time* — "carousel" would weld the layout column to VARCHAR(8), and
# the next layout anyone adds would need a migration to widen it. That is exactly
# how ``messages.category`` ended up pinned to VARCHAR(13).
_ENUM_LENGTH: int = 32


class UserDisplay(AuditMixin, MappedAsDataclass, Base):
    """One user's display page: title, blurb, layout choice."""

    __tablename__ = "user_displays"
    # Keep the AuditMixin timestamps but write no ChangeLog rows, for the same
    # reason as Message: the patch would copy the user's title, blurb, captions
    # and image guids into ``change_log.patch``, where they would survive account
    # erasure. These are photos of someone's home, not catalog content.
    __change_log_exclude__: ClassVar[bool] = True
    # The 1:1 constraint, and the ON CONFLICT target that makes the lazy
    # get-or-create in the editor route race-safe.
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_displays_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    title: Mapped[str | None] = mapped_column(Text, default=None)
    blurb: Mapped[str | None] = mapped_column(Text, default=None)
    layout: Mapped[DisplayLayout] = mapped_column(
        # ``native_enum=False`` matches every other enum column in the schema
        # (see MessageCategory): a VARCHAR with no CHECK constraint, so adding a
        # layout later needs no migration and cannot break a blue/green overlap.
        SQLAlchemyEnum(
            DisplayLayout,
            name="displaylayout",
            native_enum=False,
            length=_ENUM_LENGTH,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=DisplayLayout.collage,
        server_default=DisplayLayout.collage.value,
    )

    user: Mapped[User] = relationship(
        back_populates="display",
        foreign_keys=[user_id],
        init=False,
    )
    images: Mapped[list[UserDisplayImage]] = relationship(
        back_populates="display",
        cascade="all, delete-orphan",
        order_by=lambda: UserDisplayImage.position,
        init=False,
        default_factory=list,
        repr=False,
    )

    def __hash__(self) -> int:
        return self.id or 0

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "user_id", self.user_id
            yield "title", self.title, None
            yield "layout", self.layout
        except Exception:
            yield "detached", True
            return
        if object_session(self):
            yield "number_of_images", len(self.images)


class UserDisplayImage(AuditMixin, MappedAsDataclass, Base):
    """One photo on a display page, with an optional caption and tagged pins."""

    __tablename__ = "user_display_images"
    # See UserDisplay: captions and image guids must not be snapshotted into
    # change_log, where they would outlive an erasure request.
    __change_log_exclude__: ClassVar[bool] = True
    __table_args__ = (
        # Every read of this table is "the photos of display N, in order".
        Index(
            "ix_user_display_images_display_id_position",
            "display_id",
            "position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    display_id: Mapped[int] = mapped_column(
        ForeignKey("user_displays.id", ondelete="CASCADE"),
    )
    # Bare UUID, same convention as ``Pin.front_image_guid`` — images are objects
    # in the storage backend, not rows.
    image_guid: Mapped[UUID]

    caption: Mapped[str | None] = mapped_column(Text, default=None)
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    size_hint: Mapped[DisplayImageSize] = mapped_column(
        SQLAlchemyEnum(
            DisplayImageSize,
            name="displayimagesize",
            native_enum=False,
            length=_ENUM_LENGTH,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=DisplayImageSize.normal,
        server_default=DisplayImageSize.normal.value,
    )

    display: Mapped[UserDisplay] = relationship(
        back_populates="images",
        foreign_keys=[display_id],
        init=False,
    )
    # Which catalog pins appear in this photo. Drives the "Pins in this display"
    # strip, which is the link back into the catalog that makes a shared display
    # worth something to the site.
    pins: Mapped[list[Pin]] = relationship(
        secondary=display_image_pins,
        default_factory=list,
        repr=False,
    )

    def __hash__(self) -> int:
        return self.id or 0

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "display_id", self.display_id
            yield "image_guid", str(self.image_guid)
            yield "position", self.position
            yield "size_hint", self.size_hint
            yield "caption", self.caption, None
        except Exception:
            yield "detached", True
