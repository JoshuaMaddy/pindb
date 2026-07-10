"""Messages inbox: read, mark-read, mark-all-read, archive, unarchive.

All routes require a logged-in user. HTMX mutations swap the affected row (or the
whole list/preview) and carry an out-of-band ``#navbar-unread-dot`` update so the
navbar indicator stays in sync without re-rendering the navbar. Non-HTMX requests
fall back to a 303 redirect.
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.auth import AuthenticatedUser
from pindb.database import async_session_maker
from pindb.database.message import Message, MessageReceipt
from pindb.database.message_queries import (
    archive_statement,
    archived_count_statement,
    archived_statement,
    inbox_count_statement,
    inbox_statement,
    mark_all_read_statement,
    mark_read_statement,
    unarchive_statement,
    unread_count_statement,
    visible_clause,
)
from pindb.database.user import User
from pindb.templates.messages.components import MessageRow, Tab, message_row
from pindb.templates.messages.inbox_page import (
    LIST_SECTION_ID,
    PAGE_SIZE,
    messages_list_section,
    messages_page,
)
from pindb.templates.messages.nav_indicator import unread_dot
from pindb.templates.messages.preview import PREVIEW_ID, PREVIEW_LIMIT, messages_preview
from pindb.templates.messages.render import message_target_url

router = APIRouter(prefix="/messages", tags=["messages"])


def _resolve_tab(tab: str) -> Tab:
    return "archived" if tab == "archived" else "inbox"


async def _load_rows(
    session: AsyncSession,
    user: User,
    statement,
) -> list[MessageRow]:
    """Fetch messages and pair each with its unread flag (single receipt query)."""
    messages = list((await session.scalars(statement)).all())
    read_ids: set[int] = set()
    ids = [message.id for message in messages]
    if ids:
        rows = await session.execute(
            select(MessageReceipt.message_id).where(
                MessageReceipt.user_id == user.id,
                MessageReceipt.message_id.in_(ids),
                MessageReceipt.read_at.is_not(None),
            )
        )
        read_ids = {row[0] for row in rows}
    return [(message, message.id not in read_ids) for message in messages]


async def _unread(session: AsyncSession, user: User) -> int:
    return await session.scalar(unread_count_statement(user)) or 0


async def _assert_visible(session: AsyncSession, user: User, message_id: int) -> None:
    visible = await session.scalar(
        select(Message.id).where(Message.id == message_id, visible_clause(user))
    )
    if visible is None:
        raise HTTPException(status_code=404, detail="Message not found")


@router.get("", response_model=None, name="get_messages")
async def get_messages(
    request: Request,
    current_user: AuthenticatedUser,
    tab: str = "inbox",
    page: int = 1,
) -> HTMLResponse:
    resolved: Tab = _resolve_tab(tab)
    page = max(1, page)
    offset = (page - 1) * PAGE_SIZE

    async with async_session_maker() as session:
        if resolved == "archived":
            total = await session.scalar(archived_count_statement(current_user)) or 0
            statement = archived_statement(current_user, limit=PAGE_SIZE, offset=offset)
        else:
            total = await session.scalar(inbox_count_statement(current_user)) or 0
            statement = inbox_statement(current_user, limit=PAGE_SIZE, offset=offset)
        rows = await _load_rows(session, current_user, statement)
        unread = await _unread(session, current_user)

    if request.headers.get("HX-Target") == LIST_SECTION_ID:
        return HTMLResponse(
            str(
                messages_list_section(
                    request, rows, total=total, page=page, tab=resolved
                )
            )
        )
    return HTMLResponse(
        str(
            messages_page(
                request,
                rows,
                total=total,
                page=page,
                tab=resolved,
                unread_exists=unread > 0,
            )
        )
    )


@router.post("/read-all", response_model=None, name="mark_all_messages_read")
async def mark_all_messages_read(
    request: Request,
    current_user: AuthenticatedUser,
) -> Response:
    async with async_session_maker.begin() as session:
        await session.execute(mark_all_read_statement(current_user))

    if not request.headers.get("HX-Request"):
        return RedirectResponse(str(request.url_for("get_messages")), status_code=303)

    from_preview = request.headers.get("HX-Target") == PREVIEW_ID
    async with async_session_maker() as session:
        if from_preview:
            rows = await _load_rows(
                session,
                current_user,
                inbox_statement(current_user, limit=PREVIEW_LIMIT, offset=0),
            )
            fragment = str(messages_preview(request, rows, unread_exists=False))
        else:
            total = await session.scalar(inbox_count_statement(current_user)) or 0
            rows = await _load_rows(
                session,
                current_user,
                inbox_statement(current_user, limit=PAGE_SIZE, offset=0),
            )
            fragment = str(
                messages_list_section(request, rows, total=total, page=1, tab="inbox")
            )

    return HTMLResponse(fragment + str(unread_dot(False, oob=True)))


@router.post("/{message_id}/read", response_model=None, name="mark_message_read")
async def mark_message_read(
    request: Request,
    message_id: int,
    current_user: AuthenticatedUser,
    tab: str = "inbox",
    compact: bool = False,
) -> Response:
    async with async_session_maker.begin() as session:
        await _assert_visible(session, current_user, message_id)
        await session.execute(
            mark_read_statement(message_id=message_id, user_id=current_user.id)
        )

    async with async_session_maker() as session:
        message = await session.get(Message, message_id)
        unread = await _unread(session, current_user)
        target_url = (
            message_target_url(request, message) if message is not None else None
        )

    if not request.headers.get("HX-Request"):
        return RedirectResponse(
            target_url or str(request.url_for("get_messages")), status_code=303
        )

    body = (
        str(
            message_row(
                request,
                message,
                is_unread=False,
                tab=_resolve_tab(tab),
                compact=compact,
            )
        )
        if message is not None
        else ""
    )
    response = HTMLResponse(body + str(unread_dot(unread > 0, oob=True)))
    if target_url:
        response.headers["HX-Redirect"] = target_url
    return response


@router.post("/{message_id}/archive", response_model=None, name="archive_message")
async def archive_message(
    request: Request,
    message_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    async with async_session_maker.begin() as session:
        await _assert_visible(session, current_user, message_id)
        await session.execute(
            archive_statement(message_id=message_id, user_id=current_user.id)
        )

    async with async_session_maker() as session:
        unread = await _unread(session, current_user)

    if not request.headers.get("HX-Request"):
        return RedirectResponse(str(request.url_for("get_messages")), status_code=303)
    return HTMLResponse(str(unread_dot(unread > 0, oob=True)))


@router.post("/{message_id}/unarchive", response_model=None, name="unarchive_message")
async def unarchive_message(
    request: Request,
    message_id: int,
    current_user: AuthenticatedUser,
) -> Response:
    async with async_session_maker.begin() as session:
        await _assert_visible(session, current_user, message_id)
        await session.execute(
            unarchive_statement(message_id=message_id, user_id=current_user.id)
        )

    async with async_session_maker() as session:
        unread = await _unread(session, current_user)

    if not request.headers.get("HX-Request"):
        return RedirectResponse(
            str(request.url_for("get_messages")) + "?tab=archived", status_code=303
        )
    return HTMLResponse(str(unread_dot(unread > 0, oob=True)))
