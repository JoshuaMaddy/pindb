"""Browser-level coverage for the bulk tag creation UI."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from playwright.sync_api import Locator, Page, expect


def _tag_rows(page: Page) -> Locator:
    return page.locator("#bulk-tag-tbody tr")


def _fill_row_name(page: Page, row_index: int, name: str) -> None:
    _tag_rows(page).nth(row_index).locator("td").nth(0).locator("input").fill(name)


def _set_row_category(page: Page, row_index: int, category: str) -> None:
    _tag_rows(page).nth(row_index).locator("select").nth(0).evaluate(
        """(select, category) => {
            select.tomselect.setValue(category);
        }""",
        category,
    )


def _set_row_description(page: Page, row_index: int, description: str) -> None:
    _tag_rows(page).nth(row_index).locator("textarea").fill(description)


def _add_row_alias(page: Page, row_index: int, alias: str) -> None:
    alias_input = (
        _tag_rows(page).nth(row_index).locator("td").nth(3).locator(".ts-control input")
    )
    alias_input.click()
    alias_input.fill(alias)
    option = page.locator(".ts-dropdown:visible [data-selectable]").first
    expect(option).to_contain_text(f"Add {alias}")
    option.click()


def _select_row_implication(
    page: Page,
    row_index: int,
    *,
    query: str,
    value: str,
) -> None:
    """Select an implication through the page's Tom Select load pipeline."""
    _tag_rows(page).nth(row_index).locator("select").nth(1).evaluate(
        """(select, args) => new Promise((resolve, reject) => {
            const tomSelect = select.tomselect;
            const loader = tomSelect.settings.load;
            if (!loader) {
                reject(new Error("implication select has no loader"));
                return;
            }

            loader.call(tomSelect, args.query, function(results) {
                (results || []).forEach(function(option) {
                    tomSelect.addOption(option);
                });
                if (!tomSelect.options[args.value]) {
                    reject(new Error("missing implication option: " + args.value));
                    return;
                }
                tomSelect.addItem(args.value, true);
                resolve(tomSelect.getValue());
            });
        })""",
        {"query": query, "value": value},
    )


def _ensure_row_count(page: Page, count: int) -> None:
    while _tag_rows(page).count() < count:
        page.locator("#bulk-tag-add-row").click()
    expect(_tag_rows(page)).to_have_count(count)


def _bulk_tag_column_widths(page: Page) -> list[float]:
    return page.locator(".bulk-tag-table").evaluate(
        """(table) => Array.from(table.querySelectorAll("thead th"))
            .map((cell) => cell.getBoundingClientRect().width)"""
    )


def _wait_for_bulk_option(page: Page, live_server: str, name: str) -> None:
    deadline = time.time() + 10
    url = f"{live_server}/bulk/options/tag?q={quote(name)}"
    while time.time() < deadline:
        response = page.request.get(url)
        if response.ok and any(option["value"] == name for option in response.json()):
            return
        time.sleep(0.25)
    raise AssertionError(f"bulk tag option {name!r} was not indexed in time")


def _tag_categories(
    db_handle: Callable[..., list[tuple]], names: list[str]
) -> dict[str, str]:
    rows = db_handle(
        "SELECT name, category FROM tags WHERE name = ANY(%s)",
        (names,),
    )
    return {name: category for name, category in rows}


def _tag_implications(
    db_handle: Callable[..., list[tuple]], source_names: list[str]
) -> set[tuple[str, str]]:
    rows = db_handle(
        """
        SELECT source.name, implied.name
        FROM tag_implications
        JOIN tags AS source ON source.id = tag_implications.tag_id
        JOIN tags AS implied ON implied.id = tag_implications.implied_tag_id
        WHERE source.name = ANY(%s)
        """,
        (source_names,),
    )
    return {(source, implied) for source, implied in rows}


def _transitive_implications(
    db_handle: Callable[..., list[tuple]], source_name: str
) -> set[str]:
    rows = db_handle(
        """
        WITH RECURSIVE implied_tags(implied_id, implied_name) AS (
            SELECT implied.id, implied.name
            FROM tag_implications
            JOIN tags AS source ON source.id = tag_implications.tag_id
            JOIN tags AS implied ON implied.id = tag_implications.implied_tag_id
            WHERE source.name = %s
            UNION
            SELECT implied.id, implied.name
            FROM implied_tags
            JOIN tag_implications ON tag_implications.tag_id = implied_tags.implied_id
            JOIN tags AS implied ON implied.id = tag_implications.implied_tag_id
        )
        SELECT implied_name FROM implied_tags
        """,
        (source_name,),
    )
    return {name for (name,) in rows}


def test_bulk_tag_table_body_rows_are_visible(
    admin_browser_context,
    live_server: str,
) -> None:
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/bulk/tag")

    expect(_tag_rows(page)).to_have_count(2)
    expect(_tag_rows(page).first).to_be_visible()
    first_row_box = _tag_rows(page).first.bounding_box()
    assert first_row_box is not None
    assert first_row_box["height"] > 0


def test_bulk_tag_category_dropdown_does_not_shift_column_widths(
    admin_browser_context,
    live_server: str,
) -> None:
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/bulk/tag")
    expect(_tag_rows(page)).to_have_count(2)

    before = _bulk_tag_column_widths(page)
    category_control = _tag_rows(page).first.locator("td").nth(1).locator(".ts-control")
    category_control.click()
    expect(page.locator(".ts-dropdown:visible")).to_be_visible()
    page.keyboard.type("copyright")
    after = _bulk_tag_column_widths(page)

    assert len(before) == len(after)
    assert all(
        abs(before_width - after_width) < 1
        for before_width, after_width in zip(before, after)
    )


def test_bulk_tag_ui_preserves_per_row_categories(
    admin_browser_context,
    live_server: str,
    db_handle: Callable[..., list[tuple]],
) -> None:
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/bulk/tag")
    expect(_tag_rows(page)).to_have_count(2)

    _fill_row_name(page, 0, "bulk_e2e_category_a")
    _fill_row_name(page, 1, "bulk_e2e_category_b")
    _set_row_category(page, 0, "character")
    _set_row_category(page, 1, "copyright")

    with page.expect_request(
        lambda request: request.method == "POST" and request.url.endswith("/bulk/tag")
    ) as request_info:
        with page.expect_response(
            lambda response: (
                response.request.method == "POST" and response.url.endswith("/bulk/tag")
            )
        ) as response_info:
            page.locator("#bulk-tag-submit").click()

    assert response_info.value.ok
    payload: dict[str, Any] = json.loads(request_info.value.post_data or "{}")
    assert [row["category"] for row in payload["tags"]] == [
        "character",
        "copyright",
    ]
    expect(page.locator("#bulk-tag-success-modal")).to_be_visible()
    expect(page.locator("#bulk-tag-modal-title")).to_contain_text("2 tags created")

    categories = _tag_categories(
        db_handle,
        ["bulk_e2e_category_a", "bulk_e2e_category_b"],
    )
    assert categories == {
        "bulk_e2e_category_a": "character",
        "bulk_e2e_category_b": "copyright",
    }


def test_bulk_tag_ui_toasts_client_side_errors(
    admin_browser_context,
    live_server: str,
) -> None:
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/bulk/tag")
    expect(_tag_rows(page)).to_have_count(2)

    _fill_row_name(page, 0, "bulk_e2e_duplicate")
    _fill_row_name(page, 1, "bulk_e2e_duplicate")
    page.locator("#bulk-tag-submit").click()

    expect(page.get_by_text("Fix highlighted rows before submitting.")).to_be_visible()
    expect(_tag_rows(page).nth(0)).to_have_class(re.compile(r"\brow-error\b"))
    expect(_tag_rows(page).nth(1)).to_have_class(re.compile(r"\brow-error\b"))


def test_bulk_tag_ui_persists_description_and_multiple_aliases(
    admin_browser_context,
    live_server: str,
    db_handle: Callable[..., list[tuple]],
) -> None:
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/bulk/tag")
    expect(_tag_rows(page)).to_have_count(2)

    _fill_row_name(page, 0, "bulk_e2e_alias_target")
    _set_row_description(page, 0, "Description entered through the bulk tag UI.")
    _add_row_alias(page, 0, "Alias One")
    _add_row_alias(page, 0, "Alias Two")
    _fill_row_name(page, 1, "bulk_e2e_alias_filler")

    with page.expect_response(
        lambda response: (
            response.request.method == "POST" and response.url.endswith("/bulk/tag")
        )
    ) as response_info:
        page.locator("#bulk-tag-submit").click()

    assert response_info.value.ok
    assert response_info.value.json()["failed_count"] == 0

    rows = db_handle(
        """
        SELECT tags.description, tag_aliases.alias
        FROM tags
        LEFT JOIN tag_aliases ON tag_aliases.tag_id = tags.id
        WHERE tags.name = %s
        ORDER BY tag_aliases.alias
        """,
        ("bulk_e2e_alias_target",),
    )
    assert rows == [
        ("Description entered through the bulk tag UI.", "alias_one"),
        ("Description entered through the bulk tag UI.", "alias_two"),
    ]


def test_bulk_tag_ui_creates_db_and_in_batch_implications(
    admin_browser_context,
    live_server: str,
    db_handle: Callable[..., list[tuple]],
    make_tag: Callable[..., dict[str, Any]],
) -> None:
    make_tag("bulk_e2e_c", approved=True)

    page = admin_browser_context.new_page()
    _wait_for_bulk_option(page, live_server, "bulk_e2e_c")
    page.goto(f"{live_server}/bulk/tag")
    expect(_tag_rows(page)).to_have_count(2)

    _fill_row_name(page, 0, "bulk_e2e_a")
    _fill_row_name(page, 1, "bulk_e2e_b")

    _select_row_implication(
        page,
        0,
        query="bulk_e2e_c",
        value="bulk_e2e_c",
    )
    _select_row_implication(
        page,
        1,
        query="bulk_e2e_a",
        value="bulk_e2e_a",
    )

    with page.expect_response(
        lambda response: (
            response.request.method == "POST" and response.url.endswith("/bulk/tag")
        )
    ) as response_info:
        page.locator("#bulk-tag-submit").click()

    assert response_info.value.ok
    assert _tag_implications(db_handle, ["bulk_e2e_a", "bulk_e2e_b"]) == {
        ("bulk_e2e_a", "bulk_e2e_c"),
        ("bulk_e2e_b", "bulk_e2e_a"),
    }


def test_bulk_tag_ui_supports_multiple_implications_and_chains(
    admin_browser_context,
    live_server: str,
    db_handle: Callable[..., list[tuple]],
) -> None:
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/bulk/tag")
    _ensure_row_count(page, 4)

    _fill_row_name(page, 0, "bulk_e2e_chain_a")
    _fill_row_name(page, 1, "bulk_e2e_chain_b")
    _fill_row_name(page, 2, "bulk_e2e_chain_c")
    _fill_row_name(page, 3, "bulk_e2e_chain_d")

    _select_row_implication(
        page,
        0,
        query="bulk_e2e_chain_b",
        value="bulk_e2e_chain_b",
    )
    _select_row_implication(
        page,
        0,
        query="bulk_e2e_chain_c",
        value="bulk_e2e_chain_c",
    )
    _select_row_implication(
        page,
        1,
        query="bulk_e2e_chain_c",
        value="bulk_e2e_chain_c",
    )
    _select_row_implication(
        page,
        3,
        query="bulk_e2e_chain_a",
        value="bulk_e2e_chain_a",
    )

    with page.expect_response(
        lambda response: (
            response.request.method == "POST" and response.url.endswith("/bulk/tag")
        )
    ) as response_info:
        page.locator("#bulk-tag-submit").click()

    assert response_info.value.ok
    assert response_info.value.json()["failed_count"] == 0
    assert _tag_implications(
        db_handle,
        ["bulk_e2e_chain_a", "bulk_e2e_chain_b", "bulk_e2e_chain_d"],
    ) == {
        ("bulk_e2e_chain_a", "bulk_e2e_chain_b"),
        ("bulk_e2e_chain_a", "bulk_e2e_chain_c"),
        ("bulk_e2e_chain_b", "bulk_e2e_chain_c"),
        ("bulk_e2e_chain_d", "bulk_e2e_chain_a"),
    }
    assert _transitive_implications(db_handle, "bulk_e2e_chain_d") == {
        "bulk_e2e_chain_a",
        "bulk_e2e_chain_b",
        "bulk_e2e_chain_c",
    }
