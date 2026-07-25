"""User collection add via HTTP request after login."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.fixtures.e2e_users import REGULAR


@pytest.mark.slow
def test_collection_add_and_remove(make_pin, anon_browser_context, live_server):
    pin = make_pin("CollectionSeedPin")

    page = anon_browser_context.new_page()
    page.goto(f"{live_server}/auth/login")
    page.fill("input[name='username']", REGULAR.username)
    page.fill("input[name='password']", REGULAR.password)
    page.click("button[type='submit']")
    page.wait_for_load_state("load")

    add = page.request.post(
        f"{live_server}/user/pins/{pin['id']}/owned",
        form={"quantity": "1"},
    )
    assert add.ok, f"add-to-collection POST failed: {add.status} {add.text()[:200]}"

    page.goto(f"{live_server}/user/{REGULAR.username}/collection")
    expect(page.locator("body")).to_contain_text("CollectionSeedPin")
