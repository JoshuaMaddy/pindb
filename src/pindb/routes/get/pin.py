from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import CurrentUser
from pindb.database import Pin, PinSet, User, session_maker
from pindb.database.joins import user_favorite_pins
from pindb.templates.get.pin import pin_page

router = APIRouter()


@router.get(path="/pin/{id}", response_model=None)
def get_pin(
    request: Request,
    id: int,
    current_user: CurrentUser,
) -> HTMLResponse | RedirectResponse:
    with session_maker() as session:
        pin_obj: Pin | None = session.get(entity=Pin, ident=id)

        if not pin_obj:
            return RedirectResponse(url="/")

        is_favorited = False
        user_sets: list[PinSet] = []

        if current_user is not None:
            user: User | None = session.get(User, current_user.id)
            if user is not None:
                is_favorited = bool(
                    session.execute(
                        select(user_favorite_pins).where(
                            user_favorite_pins.c.user_id == current_user.id,
                            user_favorite_pins.c.pin_id == id,
                        )
                    ).first()
                )
                user_sets = list(
                    session.scalars(
                        select(PinSet).where(PinSet.owner_id == current_user.id)
                    ).all()
                )

        return HTMLResponse(
            content=pin_page(
                request=request,
                pin=pin_obj,
                is_favorited=is_favorited,
                user_sets=user_sets,
            )
        )
