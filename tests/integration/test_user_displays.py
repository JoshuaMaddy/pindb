"""User Display pages: upload, edit, share, and the routing traps around them."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from pindb.database.user_display import (
    MAX_DISPLAY_IMAGES,
    DisplayImageSize,
    DisplayLayout,
    UserDisplay,
    UserDisplayImage,
)
from tests.factories.pin import PinFactory


@pytest.fixture
def display_pin(db_session, admin_user, seed_currencies):
    """An approved pin a regular user is allowed to tag."""
    return PinFactory(name="Tagged Display Pin", approved=True, created_by=admin_user)


def _upload(client, png_upload) -> dict:
    response = client.post(
        "/user/me/display/image",
        files={"image": png_upload},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
class TestDisplayUpload:
    def test_guest_cannot_upload(self, client, png_upload):
        response = client.post("/user/me/display/image", files={"image": png_upload})
        assert response.status_code == 401

    def test_upload_creates_display_lazily_and_only_once(
        self, auth_client, db_session, test_user, png_upload
    ):
        assert (
            db_session.scalar(
                select(UserDisplay).where(UserDisplay.user_id == test_user.id)
            )
            is None
        )

        first = _upload(auth_client, png_upload)
        second = _upload(auth_client, png_upload)

        assert first["position"] == 0
        assert second["position"] == 1

        displays = list(
            db_session.scalars(
                select(UserDisplay).where(UserDisplay.user_id == test_user.id)
            ).all()
        )
        assert len(displays) == 1, "get-or-create must not insert a second row"

    def test_rejects_non_image(self, auth_client):
        response = auth_client.post(
            "/user/me/display/image",
            files={"image": ("not.png", b"definitely not an image", "image/png")},
        )
        assert response.status_code == 422

    def test_enforces_image_cap(
        self, auth_client, db_session, test_user, png_upload, png_bytes
    ):
        display = UserDisplay(user_id=test_user.id)
        db_session.add(display)
        db_session.flush()
        for position in range(MAX_DISPLAY_IMAGES):
            db_session.add(
                UserDisplayImage(
                    display_id=display.id,
                    image_guid=uuid.uuid4(),
                    position=position,
                )
            )
        db_session.commit()

        response = auth_client.post(
            "/user/me/display/image", files={"image": png_upload}
        )
        assert response.status_code == 422
        assert str(MAX_DISPLAY_IMAGES) in response.text


@pytest.mark.integration
class TestDisplayEditing:
    def test_caption_size_and_pins_persist(
        self, auth_client, db_session, png_upload, display_pin
    ):
        image = _upload(auth_client, png_upload)

        response = auth_client.post(
            f"/user/me/display/images/{image['id']}",
            data={
                "caption": "  My shadow box  ",
                "size_hint": "wide",
                "pin_ids": [str(display_pin.id)],
            },
        )
        assert response.status_code == 204

        db_session.expire_all()
        row = db_session.get(UserDisplayImage, image["id"])
        assert row.caption == "My shadow box"
        assert row.size_hint is DisplayImageSize.wide
        assert [pin.id for pin in row.pins] == [display_pin.id]

        # Untagging the last pin has to stick. An empty list sends no form field
        # at all, which means "leave the pins alone" — so the client sends one
        # empty string to say "explicitly none". This is the wire contract the
        # island relies on; break it and removing the last pin silently no-ops.
        auth_client.post(
            f"/user/me/display/images/{image['id']}", data={"pin_ids": [""]}
        )
        db_session.expire_all()
        assert db_session.get(UserDisplayImage, image["id"]).pins == []

        # And an omitted field must genuinely leave them alone.
        auth_client.post(
            f"/user/me/display/images/{image['id']}",
            data={"pin_ids": [str(display_pin.id)]},
        )
        auth_client.post(
            f"/user/me/display/images/{image['id']}", data={"caption": "just this"}
        )
        db_session.expire_all()
        assert [
            pin.id for pin in db_session.get(UserDisplayImage, image["id"]).pins
        ] == [display_pin.id]

    def test_reorder_persists_positions(self, auth_client, db_session, png_upload):
        first = _upload(auth_client, png_upload)
        second = _upload(auth_client, png_upload)

        response = auth_client.post(
            "/user/me/display/images/reorder",
            data={"image_ids": [str(second["id"]), str(first["id"])]},
        )
        assert response.status_code == 204

        db_session.expire_all()
        assert db_session.get(UserDisplayImage, second["id"]).position == 0
        assert db_session.get(UserDisplayImage, first["id"]).position == 1

    def test_cannot_edit_another_users_image(
        self, auth_client, admin_client, db_session, png_upload
    ):
        victim_image = _upload(admin_client, png_upload)

        response = auth_client.post(
            f"/user/me/display/images/{victim_image['id']}",
            data={"caption": "defaced"},
        )
        assert response.status_code == 403

        db_session.expire_all()
        assert db_session.get(UserDisplayImage, victim_image["id"]).caption is None

    def test_reorder_cannot_touch_another_users_images(
        self, auth_client, admin_client, db_session, png_upload
    ):
        victim_first = _upload(admin_client, png_upload)
        victim_second = _upload(admin_client, png_upload)

        # A forged id list must be a no-op, not a shuffle of someone else's photos.
        response = auth_client.post(
            "/user/me/display/images/reorder",
            data={"image_ids": [str(victim_second["id"]), str(victim_first["id"])]},
        )
        assert response.status_code == 204

        db_session.expire_all()
        assert db_session.get(UserDisplayImage, victim_first["id"]).position == 0
        assert db_session.get(UserDisplayImage, victim_second["id"]).position == 1

    def test_delete_hides_image_from_the_page(self, auth_client, test_user, png_upload):
        image = _upload(auth_client, png_upload)
        assert (
            auth_client.post(
                f"/user/me/display/images/{image['id']}/delete"
            ).status_code
            == 204
        )

        page = auth_client.get(f"/user/{test_user.username}/display")
        assert page.status_code == 200
        assert image["guid"] not in page.text

    def test_layout_change_persists(self, auth_client, db_session, test_user):
        assert (
            auth_client.post(
                "/user/me/display", data={"layout": "carousel"}
            ).status_code
            == 204
        )

        db_session.expire_all()
        display = db_session.scalar(
            select(UserDisplay).where(UserDisplay.user_id == test_user.id)
        )
        assert display.layout is DisplayLayout.carousel

    def test_invalid_layout_rejected(self, auth_client):
        response = auth_client.post("/user/me/display", data={"layout": "spiral"})
        assert response.status_code == 422


@pytest.mark.integration
class TestPinOptions:
    def test_plain_user_can_search_pins(self, auth_client, display_pin):
        """The whole reason this endpoint exists.

        ``/get/options/pin`` is editor-gated, so a regular user tagging pins in
        their own photo would get a 403 from it. Regressing this back onto the
        shared endpoint breaks the feature for everyone who isn't an editor.
        """
        response = auth_client.get(
            "/user/me/display/pin-options", params={"q": display_pin.name}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_guest_cannot_search_pins(self, client):
        assert client.get("/user/me/display/pin-options").status_code == 401


@pytest.mark.integration
class TestMemberVisibleDisplayPage:
    """The display page is members-only now — no unfurl card, no guests."""

    def test_member_sees_another_users_display(
        self, auth_client, admin_client, test_user, png_upload
    ):
        _upload(auth_client, png_upload)
        auth_client.post("/user/me/display", data={"blurb": "My whole wall."})

        page = admin_client.get(f"/user/{test_user.username}/display")
        assert page.status_code == 200
        assert "My whole wall." in page.text

    def test_guest_is_denied(self, auth_client, anon_client, test_user, png_upload):
        _upload(auth_client, png_upload)
        response = anon_client.get(
            f"/user/{test_user.username}/display", follow_redirects=False
        )
        assert response.status_code == 401

    def test_page_carries_no_share_card(self, auth_client, test_user, png_upload):
        _upload(auth_client, png_upload)
        page = auth_client.get(f"/user/{test_user.username}/display")
        assert 'property="og:' not in page.text
        assert "/get/og-image/" not in page.text

    def test_user_with_no_display_is_an_empty_page_not_a_404(
        self, auth_client, test_user
    ):
        # Still not a 404: a link passed between members must not break.
        response = auth_client.get(f"/user/{test_user.username}/display")
        assert response.status_code == 200
        assert "No display photos yet" in response.text

    def test_unknown_user_is_a_404(self, auth_client):
        assert auth_client.get("/user/nobody-here/display").status_code == 404

    def test_me_does_not_collide_with_the_username_route(self, auth_client):
        """``/user/me/display/edit`` must not be read as username="me"."""
        response = auth_client.get("/user/me/display/edit")
        assert response.status_code == 200
        assert "Edit Display" in response.text


@pytest.mark.integration
class TestProfileSection:
    def test_display_strip_links_to_the_display_page(
        self, auth_client, test_user, png_upload
    ):
        _upload(auth_client, png_upload)
        profile = auth_client.get(f"/user/{test_user.username}")
        assert profile.status_code == 200
        assert f"/user/{test_user.username}/display" in profile.text
