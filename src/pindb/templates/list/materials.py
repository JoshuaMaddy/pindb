from typing import Sequence

from fastapi import Request
from htpy import Element, p, span

from pindb.database.material import Material
from pindb.models.list_view import EntityListView
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.entity_grid_card import entity_grid_card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import DEFAULT_PER_PAGE, base_list, entity_list_section


def _grid_items(
    request: Request,
    materials: Sequence[Material],
) -> list[Element]:
    return [
        entity_grid_card(
            request=request,
            href=str(request.url_for("get_material", id=material.id)),
            pins=material.pins,
            name=("(P) " + material.name) if material.is_pending else material.name,
        )
        for material in materials
    ]


def _detailed_items(
    request: Request,
    materials: Sequence[Material],
) -> list[Element]:
    return [
        card(
            href=request.url_for("get_material", id=material.id),
            content=[
                thumbnail_grid(request=request, pins=material.pins),
                p(class_="text-lg")[
                    ("(P) " + material.name) if material.is_pending else material.name,
                    span(class_="text-pin-base-300 ml-1")[f"({len(material.pins)})"],
                ],
            ],
        )
        for material in materials
    ]


def materials_list_section(
    request: Request,
    materials: Sequence[Material],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    items: list[Element] = (
        _grid_items(request=request, materials=materials)
        if view == EntityListView.grid
        else _detailed_items(request=request, materials=materials)
    )
    return entity_list_section(
        items=items,
        page=page,
        total_count=total_count,
        base_url=base_url,
        view=view,
        per_page=per_page,
    )


def materials_list(
    request: Request,
    materials: Sequence[Material],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    return base_list(
        title="Materials",
        icon="anvil",
        request=request,
        section=materials_list_section(
            request=request,
            materials=materials,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            per_page=per_page,
        ),
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Materials",
            ]
        ),
    )
