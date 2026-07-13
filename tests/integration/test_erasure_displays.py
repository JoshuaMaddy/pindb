"""Account erasure must take display photos with it — rows *and* bytes.

Pin art survives an erasure, anonymised, because it belongs to catalog pins that
outlive the account. A display photo is a picture of the inside of someone's
home, nothing else references it, and "delete my account" has to mean the file
is gone.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database.content_report import ContentReport
from pindb.database.joins import display_image_pins
from pindb.database.user_display import UserDisplay, UserDisplayImage
from pindb.file_handler import THUMBNAIL_SIZES, image_file_path, thumbnail_storage_key


@pytest.mark.integration
class TestErasureWithDisplays:
    def test_erasure_removes_the_display_its_photos_and_their_bytes(
        self, auth_client, admin_client, db_session, test_user, png_upload
    ):
        username: str = test_user.username

        upload = auth_client.post("/user/me/display/image", files={"image": png_upload})
        assert upload.status_code == 200
        image = upload.json()
        guid: str = image["guid"]

        # The original and every derived thumbnail exist before erasure.
        assert image_file_path(guid) is not None
        thumb_keys = [thumbnail_storage_key(guid, w) for w in THUMBNAIL_SIZES]
        assert all(image_file_path(key) is not None for key in thumb_keys)

        # Someone reported the photo; that report must not outlive its target.
        _ = admin_client.post(
            "/report",
            data={
                "target_type": "display_image",
                "target_id": str(image["id"]),
                "reason": "Reported before the account was erased.",
            },
        )
        assert db_session.scalar(select(ContentReport)) is not None

        response = auth_client.post(
            "/user/me/delete-account", data={"confirm_username": username}
        )
        assert response.status_code in (200, 303)

        db_session.expire_all()
        assert db_session.scalar(select(UserDisplay)) is None
        assert db_session.scalar(select(UserDisplayImage)) is None
        assert db_session.execute(select(display_image_pins)).first() is None
        # No FK ties a report to its target, so nothing cascades — erasure has to
        # remove reports against the erased content by hand or they dangle.
        assert db_session.scalar(select(ContentReport)) is None

        # And the bytes are actually gone, not merely unreferenced.
        assert image_file_path(guid) is None
        assert all(image_file_path(key) is None for key in thumb_keys)

    def test_reports_the_user_filed_survive_anonymised(
        self, auth_client, admin_client, db_session, test_user, png_upload
    ):
        """An abuse report should outlive its reporter closing their account."""
        victim_image = admin_client.post(
            "/user/me/display/image", files={"image": png_upload}
        ).json()

        auth_client.post(
            "/report",
            data={
                "target_type": "display_image",
                "target_id": str(victim_image["id"]),
                "reason": "This is spam and an admin should still see it.",
            },
        )

        auth_client.post(
            "/user/me/delete-account",
            data={"confirm_username": test_user.username},
        )

        db_session.expire_all()
        report = db_session.scalar(select(ContentReport))
        assert report is not None, "the report itself must survive"
        assert report.reporter_id is None, "but the reporter must be anonymised"
