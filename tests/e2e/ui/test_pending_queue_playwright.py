"""Admin pending-approval queue content (Playwright)."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import set_markdown_field, submit_content_form


@pytest.mark.slow
class TestPendingQueueContent:
    def test_editor_submission_appears_in_admin_queue_with_metadata(
        self, admin_browser_context, editor_browser_context, live_server
    ):
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/create/shop")
        editor_page.fill("input[name='name']", "Queued Shop")
        set_markdown_field(editor_page, "description", "Pending review by an admin.")
        submit_content_form(editor_page)

        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
        expect(
            admin_page.get_by_role("heading", name="Pending Approvals")
        ).to_be_visible()
        expect(admin_page.get_by_role("heading", name="Shops")).to_be_visible()

        row = admin_page.locator("tr", has_text="Queued Shop")
        expect(row).to_be_visible()
        expect(row).to_contain_text("e2e_editor_pw")
        expect(row.get_by_role("button", name="Approve")).to_be_visible()
        expect(row.get_by_role("button", name="Reject")).to_be_visible()
        expect(row.get_by_role("button", name="Delete")).to_be_visible()


class TestPendingQueueEmptyState:
    def test_pending_queue_renders_when_visited(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/admin/pending")
        expect(page.get_by_role("heading", name="Pending Approvals")).to_be_visible()
        expect(
            page.get_by_text(
                "Review and approve or reject pending entries", exact=False
            )
        ).to_be_visible()
