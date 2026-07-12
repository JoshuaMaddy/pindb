"""Content reports: filing one, and the admin queue that resolves them."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database.content_report import (
    MIN_REPORT_REASON_LENGTH,
    ContentReport,
    ReportStatus,
)
from pindb.database.user_display import UserDisplayImage

GOOD_REASON = "This isn't a pin display, it's just spam."


def _upload(client, png_upload) -> dict:
    response = client.post("/user/me/display/image", files={"image": png_upload})
    assert response.status_code == 200, response.text
    return response.json()


def _report(client, image_id: int, reason: str = GOOD_REASON):
    return client.post(
        "/report",
        data={
            "target_type": "display_image",
            "target_id": str(image_id),
            "reason": reason,
        },
    )


@pytest.mark.integration
class TestFilingAReport:
    def test_guest_cannot_report(self, client, admin_client, png_upload):
        image = _upload(admin_client, png_upload)
        assert _report(client, image["id"]).status_code == 401

    def test_report_is_recorded(
        self, auth_client, admin_client, db_session, png_upload, test_user
    ):
        image = _upload(admin_client, png_upload)
        response = _report(auth_client, image["id"])
        assert response.status_code in (200, 303)

        report = db_session.scalar(select(ContentReport))
        assert report is not None
        assert report.target_id == image["id"]
        assert report.reporter_id == test_user.id
        assert report.status is ReportStatus.open

    def test_reason_must_say_something(
        self, auth_client, admin_client, db_session, png_upload
    ):
        image = _upload(admin_client, png_upload)
        response = _report(auth_client, image["id"], reason="bad")
        assert response.status_code == 422
        assert str(MIN_REPORT_REASON_LENGTH) in response.text
        assert db_session.scalar(select(ContentReport)) is None

    def test_duplicate_report_is_absorbed_silently(
        self, auth_client, admin_client, db_session, png_upload
    ):
        image = _upload(admin_client, png_upload)
        assert _report(auth_client, image["id"]).status_code in (200, 303)
        assert _report(auth_client, image["id"]).status_code in (200, 303)

        reports = list(db_session.scalars(select(ContentReport)).all())
        assert len(reports) == 1, "the unique constraint must not surface as a 500"

    def test_unknown_target_is_a_404(self, auth_client):
        assert _report(auth_client, 999999).status_code == 404


@pytest.mark.integration
class TestAdminQueue:
    def test_non_admin_cannot_see_the_queue(self, auth_client):
        assert auth_client.get("/admin/reports").status_code == 403

    def test_dismiss_closes_the_report_and_keeps_the_content(
        self, auth_client, admin_client, db_session, png_upload
    ):
        image = _upload(admin_client, png_upload)
        _report(auth_client, image["id"])
        report = db_session.scalar(select(ContentReport))

        assert (
            admin_client.post(f"/admin/reports/{report.id}/dismiss").status_code == 200
        )

        db_session.expire_all()
        assert db_session.get(ContentReport, report.id).status is ReportStatus.dismissed
        assert db_session.get(UserDisplayImage, image["id"]).deleted_at is None

    def test_removing_content_closes_every_open_report_against_it(
        self,
        auth_client,
        admin_client,
        editor_client,
        db_session,
        png_upload,
    ):
        image = _upload(admin_client, png_upload)
        _report(auth_client, image["id"])
        _report(editor_client, image["id"])

        reports = list(db_session.scalars(select(ContentReport)).all())
        assert len(reports) == 2

        response = admin_client.post(f"/admin/reports/{reports[0].id}/delete-content")
        assert response.status_code == 200

        db_session.expire_all()
        # The sibling report names a target that no longer renders. Leaving it
        # open means the queue keeps asking about content that is already gone.
        for report in reports:
            assert (
                db_session.get(ContentReport, report.id).status is ReportStatus.actioned
            )
        # The photo is soft-deleted, so the audit loader filter hides it from
        # every ordinary read — including this one. Ask for it explicitly.
        removed = db_session.get(
            UserDisplayImage,
            image["id"],
            execution_options={"include_deleted": True},
        )
        assert removed.deleted_at is not None

    def test_queue_renders_when_the_target_is_already_gone(
        self, auth_client, admin_client, db_session, png_upload
    ):
        """A report can outlive its target — no FK, nothing cascades."""
        image = _upload(admin_client, png_upload)
        _report(auth_client, image["id"])
        admin_client.post(f"/user/me/display/images/{image['id']}/delete")

        page = admin_client.get("/admin/reports")
        assert page.status_code == 200
