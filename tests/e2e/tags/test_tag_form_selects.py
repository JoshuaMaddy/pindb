"""Tag create form select widgets: behavior contract for the native port.

Written against the legacy Tom Select controls (``tags/tag_form.js``) first
per the lockstep protocol; must pass unchanged after the native MultiSelect
port. Covers the three widget flavors on this form: the category
single-select (control box tinted by the selected category), the remote-load
implications multi-select, and the create-only aliases select.
"""

from __future__ import annotations

from playwright.sync_api import expect

from tests.e2e.select_helpers import (
    control_items,
    multi_add,
    selected_values,
    single_pick,
    wait_for_option_indexed,
    widget_root,
)


def _goto_create_tag(page, live_server) -> None:
    page.goto(f"{live_server}/create/tag", wait_until="networkidle")
    expect(page.locator("#tag-form")).to_be_visible()


class TestTagFormSelects:
    def test_category_pick_updates_value_and_tints_control(
        self, admin_browser_context, live_server, assert_screenshot
    ):
        page = admin_browser_context.new_page()
        _goto_create_tag(page, live_server)

        category = page.locator("#category")
        single_pick(page, category, "Character")
        assert selected_values(category) == ["character"]

        # The whole control box carries the category color scheme.
        assert_screenshot(widget_root(category), "tag-form-category-character")

    def test_aliases_create_chips(
        self, admin_browser_context, live_server, assert_screenshot
    ):
        page = admin_browser_context.new_page()
        _goto_create_tag(page, live_server)

        aliases = page.locator("#aliases")
        multi_add(page, aliases, "First Alias", create=True)
        multi_add(page, aliases, "Second Alias", create=True)

        expect(control_items(aliases)).to_have_count(2)
        assert set(selected_values(aliases)) == {"First Alias", "Second Alias"}
        assert_screenshot(widget_root(aliases), "tag-form-alias-chips")

    def test_full_create_roundtrip_with_implication(
        self, admin_browser_context, live_server, make_tag, db_handle
    ):
        parent = make_tag("tagform_parent", approved=True)

        page = admin_browser_context.new_page()
        _goto_create_tag(page, live_server)

        implications = page.locator("#implication_ids")
        options_url = implications.get_attribute("data-options-url")
        assert options_url
        wait_for_option_indexed(page, options_url, parent["name"])

        page.locator("#name").fill("tagform_child")
        single_pick(page, page.locator("#category"), "Species")
        # Query the first name chunk: the search backend doesn't split
        # "tagform_parent" on underscores, while the widget filters loaded
        # options against the rendered text ("Tagform Parent").
        multi_add(page, implications, "tagform", option_text="tagform parent")
        multi_add(page, page.locator("#aliases"), "Tagform Child Alias", create=True)

        with page.expect_response(
            lambda r: r.request.method == "POST" and "/create/tag" in r.url
        ) as response_info:
            page.locator("#tag-form-submit").click()
        assert response_info.value.status < 400

        rows = db_handle(
            "SELECT category FROM tags WHERE name = %s", ("tagform_child",)
        )
        assert rows == [("species",)]
        implication_rows = db_handle(
            """SELECT parent.name FROM tag_implications ti
               JOIN tags child ON child.id = ti.tag_id
               JOIN tags parent ON parent.id = ti.implied_tag_id
               WHERE child.name = %s""",
            ("tagform_child",),
        )
        assert [name for (name,) in implication_rows] == ["tagform_parent"]
        alias_rows = db_handle(
            """SELECT tag_aliases.alias FROM tag_aliases
               JOIN tags ON tags.id = tag_aliases.tag_id
               WHERE tags.name = %s""",
            ("tagform_child",),
        )
        assert [alias for (alias,) in alias_rows] == ["tagform_child_alias"]
