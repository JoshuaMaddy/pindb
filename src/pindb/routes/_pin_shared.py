"""Shared FastAPI Form param class and helpers for create/edit pin routes."""

from datetime import date
from typing import Annotated

from fastapi import Form
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.model_utils import (
    empty_str_list_to_none,
    empty_str_to_none,
)
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType


class PinFormParams:
    """FastAPI ``Depends()`` class consolidating shared pin form fields.

    ``front_image`` and ``back_image`` are kept on the route signatures
    because their requiredness differs (front required on create, optional
    on edit; back optional on both).
    """

    def __init__(
        self,
        name: str = Form(),
        description: Annotated[
            str | None,
            Form(),
            BeforeValidator(func=empty_str_to_none),
        ] = None,
        acquisition_type: AcquisitionType = Form(),
        grade_names: list[str] = Form(),
        grade_prices: list[str] = Form(),
        currency_id: int = Form(default=999),
        shop_ids: list[int] = Form(default_factory=list),
        tag_ids: list[int] = Form(default_factory=list),
        pin_sets_ids: list[int] = Form(default_factory=list),
        artist_ids: list[int] = Form(default_factory=list),
        variant_pin_ids: list[int] = Form(default_factory=list),
        unauthorized_copy_pin_ids: list[int] = Form(default_factory=list),
        number_produced: Annotated[
            int | None,
            Form(),
            BeforeValidator(func=empty_str_to_none),
        ] = None,
        limited_edition: bool | None = Form(default=None),
        release_date: Annotated[
            date | None,
            Form(),
            BeforeValidator(func=empty_str_to_none),
        ] = None,
        end_date: Annotated[
            date | None,
            Form(),
            BeforeValidator(func=empty_str_to_none),
        ] = None,
        funding_type: FundingType | None = Form(default=None),
        posts: int = Form(default=1),
        width: Annotated[
            str | None,
            Form(),
            BeforeValidator(func=empty_str_to_none),
        ] = None,
        height: Annotated[
            str | None,
            Form(),
            BeforeValidator(func=empty_str_to_none),
        ] = None,
        links: Annotated[
            list[str] | None,
            Form(),
            BeforeValidator(func=empty_str_list_to_none),
        ] = None,
    ):
        self.name = name
        self.description = description
        self.acquisition_type = acquisition_type
        self.grade_names = grade_names
        self.grade_prices = grade_prices
        self.currency_id = currency_id
        self.shop_ids = shop_ids
        self.tag_ids = tag_ids
        self.pin_sets_ids = pin_sets_ids
        self.artist_ids = artist_ids
        self.variant_pin_ids = variant_pin_ids
        self.unauthorized_copy_pin_ids = unauthorized_copy_pin_ids
        self.number_produced = number_produced
        self.limited_edition = limited_edition
        self.release_date = release_date
        self.end_date = end_date
        self.funding_type = funding_type
        self.posts = posts
        self.width = width
        self.height = height
        self.links = links


def load_pin_relations(
    *,
    session: Session,
    shop_ids: list[int],
    pin_sets_ids: list[int],
    artist_ids: list[int],
) -> tuple[set[Shop], set[PinSet], set[Artist]]:
    """Resolve M2M id lists to model sets in one session pass."""
    pin_shops: set[Shop] = set(
        session.scalars(select(Shop).where(Shop.id.in_(shop_ids))).all()
    )
    pin_sets: set[PinSet] = set(
        session.scalars(select(PinSet).where(PinSet.id.in_(pin_sets_ids))).all()
    )
    pin_artists: set[Artist] = set(
        session.scalars(select(Artist).where(Artist.id.in_(artist_ids))).all()
    )
    return pin_shops, pin_sets, pin_artists


def load_pin_links(
    *,
    session: Session,
    self_pin_id: int | None,
    variant_pin_ids: list[int],
    unauthorized_copy_pin_ids: list[int],
) -> tuple[set[Pin], set[Pin]]:
    """Resolve variant / unauthorized-copy id lists to ``Pin`` sets.

    Filters out ``self_pin_id`` defensively so the symmetric mirror helper
    never tries to insert a self-reference (the DB check constraint would
    otherwise reject it at commit time).
    """
    variant_ids = [pid for pid in variant_pin_ids if pid != self_pin_id]
    copy_ids = [pid for pid in unauthorized_copy_pin_ids if pid != self_pin_id]
    variants: set[Pin] = (
        set(session.scalars(select(Pin).where(Pin.id.in_(variant_ids))).all())
        if variant_ids
        else set()
    )
    copies: set[Pin] = (
        set(session.scalars(select(Pin).where(Pin.id.in_(copy_ids))).all())
        if copy_ids
        else set()
    )
    return variants, copies


def parse_grade_dicts(
    grade_names: list[str], grade_prices: list[str]
) -> list[dict[str, object]]:
    """Zip name/price form arrays into ``[{"name", "price"}, ...]`` dicts.

    Skips entries with blank names; stripped empty price → ``None``.
    """
    parsed: list[dict[str, object]] = []
    for grade_name, price_str in zip(grade_names, grade_prices):
        if not grade_name.strip():
            continue
        stripped_price = price_str.strip()
        parsed.append(
            {
                "name": grade_name,
                "price": float(stripped_price) if stripped_price else None,
            }
        )
    return parsed
