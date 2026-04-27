"""
htpy page and fragment builders: `templates/user/profile.py`.
"""

from fastapi import Request
from htpy import Element, hr

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading
from pindb.templates.user.profile_sections import (
    _collection_section,
    _favorites_section,
    _sets_section,
    _tradeable_section,
    _want_list_section,
)
from pindb.templates.user.profile_settings import (
    settings_section,
)


def user_profile_page(
    request: Request,
    profile_user: User,
    favorite_pins: list[Pin],
    favorite_count: int,
    personal_sets: list[PinSet],
    owned_pins: list[UserOwnedPin],
    owned_count: int,
    wanted_pins: list[UserWantedPin],
    wanted_count: int,
    tradeable_entries: list[UserOwnedPin],
    tradeable_count: int,
    current_user: User | None,
) -> Element:
    username: str = profile_user.username
    is_own_profile: bool = (
        current_user is not None and current_user.id == profile_user.id
    )

    return html_base(
        title=f"{username}'s Profile",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="user",
                    text=username,
                ),
                hr,
                _favorites_section(
                    request=request,
                    pins=favorite_pins,
                    total=favorite_count,
                    username=username,
                ),
                hr,
                _sets_section(
                    request=request,
                    sets=personal_sets,
                    profile_user=profile_user,
                    current_user=current_user,
                ),
                hr,
                _collection_section(
                    request=request,
                    owned_pins=owned_pins,
                    total=owned_count,
                    username=username,
                ),
                hr,
                _want_list_section(
                    request=request,
                    wanted_pins=wanted_pins,
                    total=wanted_count,
                    username=username,
                ),
                hr,
                _tradeable_section(
                    request=request,
                    tradeable_entries=tradeable_entries,
                    total=tradeable_count,
                    username=username,
                ),
                is_own_profile and hr,
                is_own_profile
                and settings_section(
                    request=request,
                    current_user=current_user,
                ),
            ],
            flex=True,
            col=True,
        ),
    )
