"""User Display pages: the public showcase and the owner's editor.

Route-ordering trap: ``/user/me/display/edit`` and ``/user/{username}/display``
are the same shape to the router, so ``me`` would match ``{username}``. Every
``/me/...`` route in this module is therefore declared **before** the public one,
and this router is included from ``routes/user/router.py`` before its
``/{username}`` catch-all. Get either wrong and the owner routes 404 with "User
not found", which reads like a template bug rather than a routing one.

No ``refresh_user_stats`` calls here on purpose: ``UserStats`` counts
contributions to the *catalog*, and a photo of your own shelf is not one. Do not
"fix" the omission.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.routing import APIRouter
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pindb.auth import AuthenticatedUser, CurrentUser
from pindb.database import async_session_maker
from pindb.database.pin import Pin
from pindb.database.user import User
from pindb.database.user_display import (
    MAX_DISPLAY_IMAGES,
    DisplayImageSize,
    DisplayLayout,
    ObjectFit,
    UserDisplay,
    UserDisplayImage,
)
from pindb.file_handler import save_image
from pindb.htmx_toast import redirect_or_htmx_toast
from pindb.search.search import search_pin
from pindb.templates.components.pins.pin_thumbnail import thumb_image_url
from pindb.templates.user.display_edit import display_edit_page
from pindb.templates.user.display_page import user_display_page
from pindb.utils import utc_now

router = APIRouter(tags=["user"])

_PIN_OPTIONS_LIMIT: int = 30


async def _get_or_create_display(session: AsyncSession, user_id: int) -> UserDisplay:
    """Return the user's display row, creating it on first use.

    Displays are created lazily rather than at signup so accounts that never use
    the feature leave no row behind. ``ON CONFLICT DO NOTHING`` against the
    unique ``user_id`` makes two concurrent first-uploads safe.
    """
    await session.execute(
        pg_insert(UserDisplay)
        .values(
            user_id=user_id,
            layout=DisplayLayout.grid.value,
            # A Core insert bypasses the ORM, so AuditMixin's `default_factory`
            # never fires and `created_at` (NOT NULL) would be null.
            created_at=utc_now(),
        )
        .on_conflict_do_nothing(index_elements=[UserDisplay.user_id])
    )
    display: UserDisplay | None = await session.scalar(
        select(UserDisplay)
        .where(UserDisplay.user_id == user_id)
        .options(
            selectinload(UserDisplay.images).selectinload(UserDisplayImage.pins),
        )
    )
    assert display is not None  # just inserted or already present
    return display


async def _load_own_image(
    session: AsyncSession, image_id: int, user: User
) -> UserDisplayImage:
    """Load a display image, or 404/403 if it isn't the caller's."""
    image: UserDisplayImage | None = await session.scalar(
        select(UserDisplayImage)
        .where(UserDisplayImage.id == image_id)
        .options(
            selectinload(UserDisplayImage.display),
            selectinload(UserDisplayImage.pins),
        )
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Display image not found")
    if image.display.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this display image")
    return image


def _image_payload(request: Request, image: UserDisplayImage) -> dict[str, Any]:
    """Serialize an image for the editor island's props / upload response."""
    return {
        "id": image.id,
        "guid": str(image.image_guid),
        "caption": image.caption or "",
        "sizeHint": image.size_hint.value,
        "objectFit": image.object_fit.value,
        "position": image.position,
        "pins": [
            {
                "value": str(pin.id),
                "text": pin.name,
                "thumbnail": thumb_image_url(request, pin.front_image_guid, w=50),
            }
            for pin in sorted(image.pins, key=lambda pin: pin.id)
        ],
    }


# ---------------------------------------------------------------------------
# Owner routes — MUST be declared before /{username}/display
# ---------------------------------------------------------------------------


@router.get("/me/display/edit", response_model=None, name="get_edit_user_display")
async def get_edit_user_display(
    request: Request,
    current_user: AuthenticatedUser,
) -> HTMLResponse:
    async with async_session_maker.begin() as db:
        display = await _get_or_create_display(db, current_user.id)
        images = [_image_payload(request, image) for image in display.images]
        content = str(
            display_edit_page(
                request=request,
                display=display,
                images=images,
                current_user=current_user,
            )
        )
    return HTMLResponse(content=content)


@router.post("/me/display", response_model=None, name="post_update_user_display")
async def post_update_user_display(
    request: Request,
    current_user: AuthenticatedUser,
    title: Annotated[str | None, Form()] = None,
    blurb: Annotated[str | None, Form()] = None,
    layout: Annotated[str | None, Form()] = None,
) -> Response:
    """Partial update: the island posts ``layout`` alone, the form posts the text."""
    if layout is not None and layout not in DisplayLayout:
        raise HTTPException(status_code=422, detail="Invalid layout")

    async with async_session_maker.begin() as db:
        display = await _get_or_create_display(db, current_user.id)
        if title is not None:
            display.title = title.strip() or None
        if blurb is not None:
            display.blurb = blurb.strip() or None
        if layout is not None:
            display.layout = DisplayLayout(layout)

    # A layout flip is an island fetch that wants no navigation; the text form is
    # a real submit that wants to land back on the page.
    if layout is not None and title is None and blurb is None:
        return Response(status_code=204)
    return redirect_or_htmx_toast(
        request=request,
        redirect_url=str(
            request.url_for("get_user_display", username=current_user.username)
        ),
        message="Display updated.",
    )


@router.post("/me/display/image", response_model=None, name="post_user_display_image")
async def post_user_display_image(
    request: Request,
    current_user: AuthenticatedUser,
    image: UploadFile = Form(),
) -> JSONResponse:
    """Ingest one photo and persist its row immediately.

    Unlike bulk pin import — which holds guids client-side until a final submit —
    each display photo *is* the resource, so it lands in the DB at upload time.

    ``save_image`` supplies the 20 MB cap (413), Pillow validation (422), EXIF/GPS
    stripping, and all five stored thumbnail widths.
    """
    async with async_session_maker.begin() as db:
        display = await _get_or_create_display(db, current_user.id)
        if len(display.images) >= MAX_DISPLAY_IMAGES:
            raise HTTPException(
                status_code=422,
                detail=f"A display holds at most {MAX_DISPLAY_IMAGES} photos.",
            )

        guid: UUID = await save_image(file=image)
        max_position: int | None = await db.scalar(
            select(func.max(UserDisplayImage.position)).where(
                UserDisplayImage.display_id == display.id
            )
        )
        row = UserDisplayImage(
            display_id=display.id,
            image_guid=guid,
            position=(max_position + 1) if max_position is not None else 0,
            # Matches what each layout always rendered before object_fit was
            # overridable — `grid` cropped, everything else letterboxed — then
            # stays put if the display's layout changes later.
            object_fit=(
                ObjectFit.cover
                if display.layout is DisplayLayout.grid
                else ObjectFit.contain
            ),
        )
        db.add(row)
        await db.flush()
        payload = _image_payload(request, row)

    return JSONResponse(content=payload)


@router.post(
    "/me/display/images/reorder",
    response_model=None,
    name="post_reorder_user_display_images",
)
async def post_reorder_user_display_images(
    current_user: AuthenticatedUser,
    image_ids: Annotated[list[int], Form()],
) -> Response:
    async with async_session_maker.begin() as db:
        display = await _get_or_create_display(db, current_user.id)
        for position, image_id in enumerate(image_ids):
            # Scoped to the caller's own display: a forged id list reorders
            # nothing rather than shuffling someone else's photos.
            await db.execute(
                update(UserDisplayImage)
                .where(
                    UserDisplayImage.id == image_id,
                    UserDisplayImage.display_id == display.id,
                )
                .values(position=position)
            )
    return Response(status_code=204)


@router.post(
    "/me/display/images/{image_id}",
    response_model=None,
    name="post_update_user_display_image",
)
async def post_update_user_display_image(
    image_id: int,
    current_user: AuthenticatedUser,
    caption: Annotated[str | None, Form()] = None,
    size_hint: Annotated[str | None, Form()] = None,
    object_fit: Annotated[str | None, Form()] = None,
    pin_ids: Annotated[list[str] | None, Form()] = None,
) -> Response:
    """Patch one photo. Every field is optional; only what is sent gets touched.

    ``pin_ids`` is a list of *strings* so that "clear every pin" is expressible at
    all. An empty list serializes to no form field whatsoever, so a `list[int]`
    could never distinguish "don't touch the pins" from "remove them all" — both
    arrive as absent, and untagging the last pin would silently no-op. Clients
    send a single empty string to mean *explicitly none*.
    """
    if size_hint is not None and size_hint not in DisplayImageSize:
        raise HTTPException(status_code=422, detail="Invalid size_hint")
    if object_fit is not None and object_fit not in ObjectFit:
        raise HTTPException(status_code=422, detail="Invalid object_fit")

    async with async_session_maker.begin() as db:
        image = await _load_own_image(db, image_id, current_user)
        if caption is not None:
            image.caption = caption.strip() or None
        if size_hint is not None:
            image.size_hint = DisplayImageSize(size_hint)
        if object_fit is not None:
            image.object_fit = ObjectFit(object_fit)
        if pin_ids is not None:
            wanted = [int(value) for value in pin_ids if value.strip()]
            # Replace wholesale — the client always sends the full set.
            pins = (
                list((await db.scalars(select(Pin).where(Pin.id.in_(wanted)))).all())
                if wanted
                else []
            )
            image.pins = pins
    return Response(status_code=204)


@router.post(
    "/me/display/images/{image_id}/delete",
    response_model=None,
    name="post_delete_user_display_image",
)
async def post_delete_user_display_image(
    image_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    """Soft-delete the row; the stored bytes stay.

    Only account erasure hard-deletes image bytes (see ``file_handler``): a
    mis-click here stays recoverable, and the audit filter already hides the row
    from every reader.
    """
    async with async_session_maker.begin() as db:
        image = await _load_own_image(db, image_id, current_user)
        image.deleted_at = utc_now()
        image.deleted_by_id = current_user.id
    return Response(status_code=204)


@router.get(
    "/me/display/pin-options",
    response_model=None,
    name="get_display_pin_options",
)
async def get_display_pin_options(
    request: Request,
    current_user: AuthenticatedUser,
    q: str = Query(default=""),
) -> JSONResponse:
    """Pin autocomplete for the display editor, open to any signed-in user.

    ``/get/options/pin`` cannot be reused: it is editor-gated because it reads
    Meilisearch directly with no DB re-hydration and would hand pending entities
    to anyone who asked. ``search_pin`` re-hydrates through the ORM, so the audit
    loader filter applies and a regular user never sees an unapproved pin.
    """
    if not q.strip():
        return JSONResponse(content=[])
    async with async_session_maker() as db:
        pins = await search_pin(query=q.strip(), session=db) or []
        return JSONResponse(
            content=[
                {
                    "value": str(pin.id),
                    "text": pin.name,
                    "thumbnail": thumb_image_url(request, pin.front_image_guid, w=50),
                }
                for pin in pins[:_PIN_OPTIONS_LIMIT]
            ]
        )


# ---------------------------------------------------------------------------
# Public display page
# ---------------------------------------------------------------------------


@router.get("/{username}/display", response_model=None, name="get_user_display")
async def get_user_display(
    request: Request,
    username: str,
    current_user: CurrentUser,
) -> HTMLResponse:
    async with async_session_maker() as db:
        profile_user: User | None = (
            await db.scalars(select(User).where(User.username == username))
        ).first()
        if profile_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        display: UserDisplay | None = await db.scalar(
            select(UserDisplay)
            .where(UserDisplay.user_id == profile_user.id)
            .options(
                selectinload(UserDisplay.images)
                .selectinload(UserDisplayImage.pins)
                .selectinload(Pin.shops),
                selectinload(UserDisplay.images)
                .selectinload(UserDisplayImage.pins)
                .selectinload(Pin.artists),
            )
        )

        # A user with no display is a 200 empty state, never a 404 — a shared
        # link must not break, and the owner needs somewhere to land.
        images = list(display.images) if display else []

        return HTMLResponse(
            content=str(
                user_display_page(
                    request=request,
                    profile_user=profile_user,
                    display=display,
                    images=images,
                    current_user=current_user,
                )
            )
        )
