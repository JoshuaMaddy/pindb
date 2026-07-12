"""Page-object helpers for e2e tests.

Each class wraps a single Playwright `Page` and exposes the small set of
domain operations a test actually needs. Keeps the test bodies focused on
*what* is being verified rather than CSS-selector minutiae.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def submit_content_form(page: Page, *, wait_for_navigation: bool = True) -> None:
    """Click the main content form's submit control.

    Two landmines this avoids:

    * ``button[type='submit']`` also matches the navbar logout button for
      authenticated users — clicking it naively logs the user out.
    * Entity create/edit forms use ``<input type='submit'>``; auth / pending
      queue forms use ``<button type='submit'>``.
    * The form is ``hx_post`` driven, so the submit triggers an HTMX request
      that returns an ``HX-Redirect`` header. The subsequent client-side
      navigation must be awaited or the test races the redirect.
    """

    def _do_click() -> None:
        inputs = page.locator("form input[type='submit']")
        if inputs.count() > 0:
            inputs.first.click()
            return
        page.locator(
            "form:not([action='/auth/logout']) button[type='submit']"
        ).first.click()

    if wait_for_navigation:
        with page.expect_navigation():
            _do_click()
    else:
        _do_click()


def submit_pending_action(page: Page, form: Locator) -> None:
    """Submit a pending-queue action form and wait for its POST to complete.

    Pending-queue action buttons post via ``hx-post`` and swap
    ``#pending-content`` in place — no navigation happens, so
    ``wait_for_load_state("load")`` resolves immediately and races the request
    (DB asserts then read pre-action state). Waiting on the POST response
    guarantees the server transaction committed; DOM assertions afterwards
    rely on Playwright's auto-retrying ``expect()`` to see the swapped
    fragment.
    """
    with page.expect_response(
        lambda response: (
            response.request.method == "POST" and "/admin/pending/" in response.url
        )
    ):
        form.locator("button[type='submit']").click()


def set_markdown_field(page: Page, name: str, value: str) -> None:
    """Set the value of a ``markdown_editor`` hidden input by name.

    The shop / artist / tag / pin forms render the description via a hidden
    ``<input name=...>`` synced from an Overtype editor (see
    ``templates/components/forms/markdown_editor.py``). ``page.fill`` can't target
    hidden inputs, so we set the value directly via JS — the form submit picks
    it up since it's still a real form field.
    """
    page.locator(f"input[name='{name}']").evaluate(
        "(el, v) => { el.value = v; }", value
    )


class _PageBase:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _settle(self) -> None:
        self.page.wait_for_load_state("load")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class NavBar:
    def __init__(self, page: Page) -> None:
        self.page = page

    def click_logout(self) -> None:
        self.page.locator("form[action='/auth/logout'] button[type='submit']").click()
        self.page.wait_for_load_state("load")


# ---------------------------------------------------------------------------
# Shops
# ---------------------------------------------------------------------------


class ShopListPage(_PageBase):
    def goto(self) -> ShopListPage:
        self.page.goto(self._url("/list/shops"))
        self._settle()
        return self

    def open_shop(self, name: str) -> None:
        self.page.get_by_text(name, exact=True).first.click()
        self._settle()

    def has_shop(self, name: str) -> bool:
        return self.page.get_by_text(name, exact=True).count() > 0


class ShopDetailPage(_PageBase):
    def goto(self, shop_id: int) -> ShopDetailPage:
        self.page.goto(self._url(f"/get/shop/{shop_id}"))
        self._settle()
        return self

    def click_edit(self) -> ShopEditPage:
        self.page.locator("a[href*='/edit/shop/']").first.click()
        self._settle()
        return ShopEditPage(self.page, self.base_url)

    def pending_edit_banner(self) -> Locator:
        return self.page.get_by_text("This entry has a pending edit awaiting approval.")

    def viewing_pending_banner(self) -> Locator:
        return self.page.get_by_text("Viewing pending edit.")


class ShopEditPage(_PageBase):
    def goto(self, shop_id: int) -> ShopEditPage:
        self.page.goto(self._url(f"/edit/shop/{shop_id}"))
        self._settle()
        return self

    def name_value(self) -> str:
        return self.page.locator("input[name='name']").input_value()

    def description_value(self) -> str:
        return self.page.locator("input[name='description']").input_value()

    def submit(
        self, *, name: str | None = None, description: str | None = None
    ) -> None:
        if name is not None:
            self.page.fill("input[name='name']", name)
        if description is not None:
            set_markdown_field(self.page, "description", description)
        submit_content_form(self.page)


# ---------------------------------------------------------------------------
# Pending queue
# ---------------------------------------------------------------------------


class PendingQueuePage(_PageBase):
    def goto(self) -> PendingQueuePage:
        self.page.goto(self._url("/admin/pending"))
        self._settle()
        return self

    # Section helpers

    def section(self, label: str) -> Locator:
        """Locator for the table that follows the given section heading."""
        return self.page.get_by_role("heading", name=label, exact=True)

    def has_section(self, label: str) -> bool:
        return self.section(label).count() > 0

    # Row helpers

    def row_for_entity(self, name: str) -> Locator:
        """First table row containing the given entity name."""
        return self.page.locator("tr", has_text=name).first

    # Action buttons (new entities)

    def approve_entity(self, entity_type: str, name: str) -> None:
        row = self.row_for_entity(name)
        submit_pending_action(
            self.page,
            row.locator(f"form[action*='/admin/pending/approve/{entity_type}/']"),
        )

    def open_change_request(self, name: str) -> Locator:
        """Open the change-request dialog from a row, returning the dialog's form.

        The reject action is the only queue action with a body, so it goes through
        the ``request-changes-modal`` island rather than a bare inline form. The
        form only exists in the DOM once the dialog is open.
        """
        row = self.row_for_entity(name)
        row.get_by_role("button", name="Request changes").first.click()
        form = self.page.locator("form[action*='/admin/pending/reject']")
        form.wait_for(state="visible")
        return form

    def request_changes(self, entity_type: str, name: str, reason: str) -> None:
        del entity_type  # the dialog is opened from the row, not by action URL
        form = self.open_change_request(name)
        form.locator("textarea[name='reason']").fill(reason)
        submit_pending_action(self.page, form)

    def delete_entity(self, entity_type: str, name: str) -> None:
        row = self.row_for_entity(name)
        submit_pending_action(
            self.page,
            row.locator(f"form[action*='/admin/pending/delete/{entity_type}/']"),
        )

    # Action buttons (pending edits)

    def approve_edits(self, entity_type: str, name: str) -> None:
        row = self.row_for_entity(name)
        submit_pending_action(
            self.page,
            row.locator(f"form[action*='/admin/pending/approve-edits/{entity_type}/']"),
        )

    def request_changes_to_edits(
        self, entity_type: str, name: str, reason: str
    ) -> None:
        del entity_type  # the dialog is opened from the row, not by action URL
        form = self.open_change_request(name)
        form.locator("textarea[name='reason']").fill(reason)
        submit_pending_action(self.page, form)

    def delete_edits(self, entity_type: str, name: str) -> None:
        row = self.row_for_entity(name)
        submit_pending_action(
            self.page,
            row.locator(f"form[action*='/admin/pending/delete-edits/{entity_type}/']"),
        )
