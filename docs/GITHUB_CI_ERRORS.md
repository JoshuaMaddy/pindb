Run uv run pytest -n auto --dist loadfile
  
============================= test session starts ==============================
platform linux -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/runner/work/pindb/pindb
configfile: pyproject.toml
testpaths: tests
plugins: base-url-2.1.0, anyio-4.10.0, Faker-40.13.0, playwright-0.7.2, xdist-3.8.0, env-1.6.0
created: 2/2 workers
2 workers [384 items]
........................................................................ [ 18%]
...............................F................F...............F....... [ 37%]
.......F..............F................................................. [ 56%]
........................................................................ [ 75%]
...........................FF.........F................FFF......FFF.FF.. [ 93%]
...........F............                                                 [100%]
=================================== FAILURES ===================================
_ TestPendingQueueContent.test_editor_submission_appears_in_admin_queue_with_metadata[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_ui_content.TestPendingQueueContent object at 0x7f6c598ed450>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
    def test_editor_submission_appears_in_admin_queue_with_metadata(
        self, admin_browser_context, editor_browser_context, live_server
    ):
        # Editor creates a pending shop.
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/create/shop")
        editor_page.fill("input[name='name']", "Queued Shop")
        set_markdown_field(editor_page, "description", "Pending review by an admin.")
        submit_content_form(editor_page)
    
        # Admin queue page renders heading, "Shops" section, and the row.
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
        expect(
            admin_page.get_by_role("heading", name="Pending Approvals")
        ).to_be_visible()
>       expect(admin_page.get_by_role("heading", name="Shops")).to_be_visible()
E       AssertionError: Locator expected to be visible
E       Actual value: None
E       Error: element(s) not found 
E       Call log:
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for get_by_text("BannerTarget").first
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
_ TestPendingEditBanner.test_anonymous_user_does_not_see_pending_edit_banner[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_ui_content.TestPendingEditBanner object at 0x7f6c598eda90>
browser = <Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
    def test_anonymous_user_does_not_see_pending_edit_banner(
        self, browser, admin_browser_context, editor_browser_context, live_server
    ):
        # Setup: admin creates a shop, editor edits it.
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/create/shop")
        admin_page.fill("input[name='name']", "AnonShopBanner")
        submit_content_form(admin_page)
        admin_page.wait_for_load_state("load")
    
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/list/shops")
>       editor_page.get_by_text("AnonShopBanner").first.click()
tests/e2e/test_ui_content.py:228: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f6c594030e0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f6c5900ccc0>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for get_by_text("AnonShopBanner").first
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
_ TestPendingEditReject.test_admin_reject_removes_edit_from_queue_and_keeps_canonical[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_ui_content.TestPendingEditReject object at 0x7f6c598edd10>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
    def test_admin_reject_removes_edit_from_queue_and_keeps_canonical(
        self, admin_browser_context, editor_browser_context, live_server
    ):
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/create/shop")
        admin_page.fill("input[name='name']", "RejectMe")
        submit_content_form(admin_page)
        admin_page.wait_for_load_state("load")
    
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/list/shops")
>       editor_page.get_by_text("RejectMe").first.click()
tests/e2e/test_ui_content.py:265: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f6c594030e0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f6c59276e80>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for get_by_text("RejectMe").first
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
_ TestThemeSwitcher.test_changing_theme_updates_html_class_without_reload[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_ui_content.TestThemeSwitcher object at 0x7f6c598edf90>
regular_user_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
db_handle = <function db_handle.<locals>._exec at 0x7f6c59274180>
    def test_changing_theme_updates_html_class_without_reload(
        self, regular_user_browser_context, live_server, db_handle
    ):
        # Use the regular user (not admin); revert the theme change at the
        # end so this test's flip doesn't leak into later tests that read
        # the default theme.
        page = regular_user_browser_context.new_page()
        try:
            page.goto(f"{live_server}/user/me", wait_until="load")
    
            # Default theme is mocha.
            expect(page.locator("html")).to_have_attribute(
                "class", re.compile(r"\bmocha\b")
            )
    
            # Pick a different theme — radios are visually hidden. ``check(force=True)``
            # does not always dispatch ``change``, which HTMX listens for; fire it explicitly.
            target = page.locator("input[name='theme'][value='dracula']").first
            expect(target).to_have_count(1)
>           with page.expect_response(
                lambda r: r.request.method == "POST" and "/user/me/settings" in r.url
            ):
tests/e2e/test_ui_content.py:311: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.13/site-packages/playwright/_impl/_sync_base.py:85: in __exit__
    self._event.value
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._sync_base.EventInfo object at 0x7f6c58e10050>
    @property
    def value(self) -> T:
        while not self._future.done():
            self._sync_base._dispatcher_fiber.switch()
        asyncio._set_running_loop(self._sync_base._loop)
        exception = self._future.exception()
        if exception:
>           raise exception
E           playwright._impl._errors.TimeoutError: Timeout 5000ms exceeded while waiting for event "response"
.venv/lib/python3.13/site-packages/playwright/_impl/_sync_base.py:59: TimeoutError
___ TestEditChainBuildup.test_two_editors_stack_edits_into_a_chain[chromium] ___
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_pending_chain.TestEditChainBuildup object at 0x7f6c59b08050>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
second_editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c58e47060>
db_handle = <function db_handle.<locals>._exec at 0x7f6c58e45260>
    def test_two_editors_stack_edits_into_a_chain(
        self,
        editor_browser_context,
        second_editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """Editor A edits → pending edit. Editor B opens, sees A's snapshot,
        submits another edit → second pending edit chained to the first.
    
        The canonical row must remain unchanged throughout.
        """
        shop = make_shop("ChainTarget", description="orig desc", approved=True)
        shop_id = int(shop["id"])
    
        # --- Editor A: rename ---
        page_a = editor_browser_context.new_page()
        ShopEditPage(page_a, live_server).goto(shop_id).submit(name="ChainTarget v2")
    
        # --- Editor B: open the edit page; the form should pre-populate with
        # the *effective* (post-A) snapshot, not the canonical name. ---
        page_b = second_editor_browser_context.new_page()
        edit_page_b = ShopEditPage(page_b, live_server).goto(shop_id)
>       assert edit_page_b.name_value() == "ChainTarget v2"
E       AssertionError: assert 'ChainTarget' == 'ChainTarget v2'
E         
E         - ChainTarget v2
E         ?            ---
E         + ChainTarget
tests/e2e/test_pending_chain.py:70: AssertionError
_ TestEditChainBuildup.test_admin_approve_edits_collapses_chain_in_order[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_pending_chain.TestEditChainBuildup object at 0x7f6c59b082d0>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
second_editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c583a00e0>
db_handle = <function db_handle.<locals>._exec at 0x7f6c583a2340>
    def test_admin_approve_edits_collapses_chain_in_order(
        self,
        editor_browser_context,
        second_editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop = make_shop("MergeMe", description="d0", approved=True)
        shop_id = int(shop["id"])
    
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="MergeMe v2")
        ShopEditPage(second_editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(description="final desc")
    
        admin_page = admin_browser_context.new_page()
>       PendingQueuePage(admin_page, live_server).goto().approve_edits(
            "shop", "MergeMe"
        )
tests/e2e/test_pending_chain.py:105: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/e2e/_pages.py:200: in approve_edits
    ).locator("button[type='submit']").click()
                                       ^^^^^^^
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f6c594030e0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f6c5835e3e0>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for locator("tr").filter(has_text="MergeMe").first.locator("form[action*='/admin/pending/approve-edits/shop/']").locator("button[type='submit']")
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
_ TestEditChainNegative.test_reject_edits_keeps_chain_invisible_but_preserved[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_pending_chain.TestEditChainNegative object at 0x7f6c59b08550>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c583d05e0>
db_handle = <function db_handle.<locals>._exec at 0x7f6c583d0860>
    def test_reject_edits_keeps_chain_invisible_but_preserved(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop = make_shop("RejectKept", approved=True)
        shop_id = int(shop["id"])
    
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="RejectKept v2")
    
        admin_page = admin_browser_context.new_page()
>       PendingQueuePage(admin_page, live_server).goto().reject_edits(
            "shop", "RejectKept"
        )
tests/e2e/test_pending_chain.py:139: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/e2e/_pages.py:207: in reject_edits
    ).locator("button[type='submit']").click()
                                       ^^^^^^^
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f6c594030e0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f6c5835c540>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for locator("tr").filter(has_text="RejectKept").first.locator("form[action*='/admin/pending/reject-edits/shop/']").locator("button[type='submit']")
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
_ TestEditChainNegative.test_delete_edits_wipes_chain_and_canonical_unchanged[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_pending_chain.TestEditChainNegative object at 0x7f6c59b087d0>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c5835eac0>
db_handle = <function db_handle.<locals>._exec at 0x7f6c5835eb60>
    def test_delete_edits_wipes_chain_and_canonical_unchanged(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop = make_shop("WipeMe", approved=True)
        shop_id = int(shop["id"])
    
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="WipeMe v2")
    
        admin_page = admin_browser_context.new_page()
>       PendingQueuePage(admin_page, live_server).goto().delete_edits("shop", "WipeMe")
tests/e2e/test_pending_chain.py:181: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/e2e/_pages.py:214: in delete_edits
    ).locator("button[type='submit']").click()
                                       ^^^^^^^
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f6c594030e0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f6c58091260>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for locator("tr").filter(has_text="WipeMe").first.locator("form[action*='/admin/pending/delete-edits/shop/']").locator("button[type='submit']")
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
______________________ test_admin_creates_shop[chromium] _______________________
[gw0] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:45901'
    def test_admin_creates_shop(admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/create/shop")
        page.fill("input[name='name']", "E2E Shop")
        set_markdown_field(page, "description", "Created via Playwright")
        submit_content_form(page)
    
        page.goto(f"{live_server}/list/shops")
>       expect(page.get_by_text("E2E Shop")).to_be_visible()
E       AssertionError: Locator expected to be visible
E       Actual value: None
E       Error: element(s) not found 
E       Call log:
E         - Expect "to_be_visible" with timeout 5000ms
E         - waiting for get_by_text("E2E Shop")
tests/e2e/test_flows.py:62: AssertionError
_ TestPendingBannerLinksWork.test_view_pending_link_navigates_to_pending_view[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_pending_chain.TestPendingBannerLinksWork object at 0x7f6c59b08a50>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c5835f100>
    def test_view_pending_link_navigates_to_pending_view(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
    ):
        shop = make_shop("BannerLink", approved=True)
        shop_id = int(shop["id"])
    
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="BannerLink v2")
    
        admin_page = admin_browser_context.new_page()
        ShopDetailPage(admin_page, live_server).goto(shop_id)
        # Banner present, with a "View pending →" link.
        link = admin_page.locator("a", has_text="View pending")
>       link.first.click()
tests/e2e/test_pending_chain.py:208: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f6c594030e0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f6c58e44ea0>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for locator("a").filter(has_text="View pending").first
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
_ TestInterleavedEdits.test_two_editors_submit_independent_edits_both_landed[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_concurrent.TestInterleavedEdits object at 0x7f6c59a7a350>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
second_editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c5900e340>
db_handle = <function db_handle.<locals>._exec at 0x7f6c5900f740>
    def test_two_editors_submit_independent_edits_both_landed(
        self,
        editor_browser_context,
        second_editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """Editor A and Editor B both open the edit page on a fresh
        approved shop, then submit different changes. Both pending edits
        should land on the chain (no clobbering)."""
        shop = make_shop("RaceShop", description="d0", approved=True)
        shop_id = int(shop["id"])
    
        # Both editors load the edit form before either submits.
        page_a = editor_browser_context.new_page()
        page_b = second_editor_browser_context.new_page()
        edit_a = ShopEditPage(page_a, live_server).goto(shop_id)
        edit_b = ShopEditPage(page_b, live_server).goto(shop_id)
    
        # Both saw the canonical name at load time.
        assert edit_a.name_value() == "RaceShop"
        assert edit_b.name_value() == "RaceShop"
    
        # Editor A submits first.
        edit_a.submit(name="RaceShop A")
        # Editor B submits next; their snapshot is now stale (they
        # still see "RaceShop"), but the system should still chain
        # their edit on top of A's.
        edit_b.submit(description="d-by-b")
    
        # Both edits accepted, canonical untouched.
>       assert _pending_edit_count(db_handle, shop_id) == 2
E       assert 0 == 2
E        +  where 0 = _pending_edit_count(<function db_handle.<locals>._exec at 0x7f6c5900f740>, 1)
tests/e2e/test_concurrent.py:72: AssertionError
_ TestInterleavedEdits.test_admin_edit_during_pending_overwrites_canonical_only[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_concurrent.TestInterleavedEdits object at 0x7f6c59a7a990>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c58bcfe20>
db_handle = <function db_handle.<locals>._exec at 0x7f6c58bcee80>
    def test_admin_edit_during_pending_overwrites_canonical_only(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """Admin can directly edit a canonical row while a pending edit
        is in flight. The pending edit chain remains intact and is
        still applicable."""
        shop = make_shop("AdminBypass", description="d0", approved=True)
        shop_id = int(shop["id"])
    
        # Editor submits an edit (becomes pending).
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="AdminBypass v2")
    
        # Admin then edits the canonical row directly (admin edits skip
        # the pending flow per `needs_pending_edit`).
        ShopEditPage(admin_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(description="d-from-admin")
    
        name, desc = _shop_row(db_handle, shop_id)
        assert name == "AdminBypass", "admin edit must not affect name"
>       assert desc == "d-from-admin", "admin edit applied to description"
E       AssertionError: admin edit applied to description
E       assert 'd0' == 'd-from-admin'
E         
E         - d-from-admin
E         + d0
tests/e2e/test_concurrent.py:102: AssertionError
_____________ test_editor_pending_edit_approved_by_admin[chromium] _____________
[gw0] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:45901'
    @pytest.mark.slow
    def test_editor_pending_edit_approved_by_admin(
        admin_browser_context, editor_browser_context, live_server
    ):
        # Admin creates the shop.
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/create/shop")
        admin_page.fill("input[name='name']", "Target Shop")
        submit_content_form(admin_page)
    
        # Editor opens the shop's edit page and submits a rename.
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/list/shops")
>       editor_page.get_by_text("Target Shop").first.click()
tests/e2e/test_flows.py:84: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f9c30cbecf0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f9c16c38720>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for get_by_text("Target Shop").first
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
_ TestInterleavedEdits.test_admin_approves_after_admin_canonical_edit[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_concurrent.TestInterleavedEdits object at 0x7f6c59a66190>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c58b7d300>
db_handle = <function db_handle.<locals>._exec at 0x7f6c58b7e5c0>
    def test_admin_approves_after_admin_canonical_edit(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """If the admin both edits canonical AND later approves the
        editor's pending edit, the editor's patch lands on top of the
        admin's intermediate state."""
        shop = make_shop("Stack", description="d0", approved=True)
        shop_id = int(shop["id"])
    
        # Editor proposes a name change.
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="Stack v2")
    
        # Admin tweaks description directly.
        ShopEditPage(admin_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(description="d-admin")
    
        # Admin then approves the editor's chain.
        admin_page = admin_browser_context.new_page()
>       PendingQueuePage(admin_page, live_server).goto().approve_edits("shop", "Stack")
tests/e2e/test_concurrent.py:133: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/e2e/_pages.py:200: in approve_edits
    ).locator("button[type='submit']").click()
                                       ^^^^^^^
.venv/lib/python3.13/site-packages/playwright/sync_api/_generated.py:15631: in click
    self._sync(
.venv/lib/python3.13/site-packages/playwright/_impl/_locator.py:162: in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.venv/lib/python3.13/site-packages/playwright/_impl/_frame.py:566: in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
self = <playwright._impl._connection.Connection object at 0x7f6c594030e0>
cb = <function Channel.send.<locals>.<lambda> at 0x7f6c58b7f920>
is_internal = False, title = None
    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)
    
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
E           Call log:
E             - waiting for locator("tr").filter(has_text="Stack").first.locator("form[action*='/admin/pending/approve-edits/shop/']").locator("button[type='submit']")
.venv/lib/python3.13/site-packages/playwright/_impl/_connection.py:559: TimeoutError
________________ test_pending_cascade_on_pin_approval[chromium] ________________
[gw0] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:45901'
    @pytest.mark.slow
    def test_pending_cascade_on_pin_approval(
        admin_browser_context, editor_browser_context, live_server
    ):
        # Editor creates a new (pending) shop via the form.
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/create/shop")
        editor_page.fill("input[name='name']", "Cascade Shop")
        submit_content_form(editor_page)
    
        # Admin sees it pending.
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
>       expect(admin_page.get_by_text("Cascade Shop")).to_be_visible()
E       AssertionError: Locator expected to be visible
E       Actual value: None
E       Error: element(s) not found 
E       Call log:
E         - Expect "to_be_visible" with timeout 5000ms
E         - waiting for get_by_text("Cascade Shop")
tests/e2e/test_flows.py:155: AssertionError
_ TestPendingBannerDisappearsAfterApprove.test_banner_gone_once_admin_approves_chain[chromium] _
[gw1] linux -- Python 3.13.13 /home/runner/work/pindb/pindb/.venv/bin/python
self = <e2e.test_concurrent.TestPendingBannerDisappearsAfterApprove object at 0x7f6c59a7ac10>
editor_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
admin_browser_context = <BrowserContext browser=<Browser type=<BrowserType name=chromium executable_path=/home/runner/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome> version=145.0.7632.6>>
live_server = 'http://127.0.0.1:36141'
make_shop = <function make_shop.<locals>._make at 0x7f6c58b7f6a0>
    def test_banner_gone_once_admin_approves_chain(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
    ):
        shop = make_shop("BannerGone", approved=True)
        shop_id = int(shop["id"])
    
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="BannerGone v2")
    
        admin_page = admin_browser_context.new_page()
        # Banner present pre-approval.
        ShopDetailPage(admin_page, live_server).goto(shop_id)
        expect(
            admin_page.get_by_text("This entry has a pending edit awaiting approval.")
>       ).to_be_visible()
          ^^^^^^^^^^^^^^^
E       AssertionError: Locator expected to be visible
E       Actual value: None
E       Error: element(s) not found 
E       Call log:
E         - Expect "to_be_visible" with timeout 5000ms
E         - waiting for get_by_text("This entry has a pending edit awaiting approval.")
tests/e2e/test_concurrent.py:167: AssertionError
=============================== warnings summary ===============================
tests/e2e/test_ui_content.py::TestNavbar::test_anonymous_navbar_shows_login_and_hides_create_admin[chromium]
tests/e2e/test_pin_creation.py::TestPinImageRoundTrip::test_uploaded_pin_image_is_retrievable_with_thumbnail[chromium]
  /home/runner/work/pindb/pindb/tests/e2e/conftest.py:189: DeprecationWarning: The wait_for_logs function with string or callable predicates is deprecated and will be removed in a future version. Use structured wait strategies instead: container.waiting_for(LogMessageWaitStrategy('ready')) or container.waiting_for(LogMessageWaitStrategy(re.compile(r'pattern')))
    wait_for_logs(container, "Server listening", timeout=30)
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/e2e/test_ui_content.py::TestPendingQueueContent::test_editor_submission_appears_in_admin_queue_with_metadata[chromium] - AssertionError: Locator expected to be visible
Actual value: None
Error: element(s) not found 
Call log:
  - Expect "to_be_visible" with timeout 5000ms
  - waiting for get_by_role("heading", name="Shops")
FAILED tests/e2e/test_ui_content.py::TestPendingEditBanner::test_canonical_shop_view_shows_pending_edit_banner_to_admin[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for get_by_text("BannerTarget").first
FAILED tests/e2e/test_ui_content.py::TestPendingEditBanner::test_anonymous_user_does_not_see_pending_edit_banner[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for get_by_text("AnonShopBanner").first
FAILED tests/e2e/test_ui_content.py::TestPendingEditReject::test_admin_reject_removes_edit_from_queue_and_keeps_canonical[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for get_by_text("RejectMe").first
FAILED tests/e2e/test_ui_content.py::TestThemeSwitcher::test_changing_theme_updates_html_class_without_reload[chromium] - playwright._impl._errors.TimeoutError: Timeout 5000ms exceeded while waiting for event "response"
FAILED tests/e2e/test_pending_chain.py::TestEditChainBuildup::test_two_editors_stack_edits_into_a_chain[chromium] - AssertionError: assert 'ChainTarget' == 'ChainTarget v2'
  
  - ChainTarget v2
  ?            ---
  + ChainTarget
FAILED tests/e2e/test_pending_chain.py::TestEditChainBuildup::test_admin_approve_edits_collapses_chain_in_order[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("tr").filter(has_text="MergeMe").first.locator("form[action*='/admin/pending/approve-edits/shop/']").locator("button[type='submit']")
FAILED tests/e2e/test_pending_chain.py::TestEditChainNegative::test_reject_edits_keeps_chain_invisible_but_preserved[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("tr").filter(has_text="RejectKept").first.locator("form[action*='/admin/pending/reject-edits/shop/']").locator("button[type='submit']")
FAILED tests/e2e/test_pending_chain.py::TestEditChainNegative::test_delete_edits_wipes_chain_and_canonical_unchanged[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("tr").filter(has_text="WipeMe").first.locator("form[action*='/admin/pending/delete-edits/shop/']").locator("button[type='submit']")
FAILED tests/e2e/test_flows.py::test_admin_creates_shop[chromium] - AssertionError: Locator expected to be visible
Actual value: None
Error: element(s) not found 
Call log:
  - Expect "to_be_visible" with timeout 5000ms
  - waiting for get_by_text("E2E Shop")
FAILED tests/e2e/test_pending_chain.py::TestPendingBannerLinksWork::test_view_pending_link_navigates_to_pending_view[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("a").filter(has_text="View pending").first
FAILED tests/e2e/test_concurrent.py::TestInterleavedEdits::test_two_editors_submit_independent_edits_both_landed[chromium] - assert 0 == 2
 +  where 0 = _pending_edit_count(<function db_handle.<locals>._exec at 0x7f6c5900f740>, 1)
FAILED tests/e2e/test_concurrent.py::TestInterleavedEdits::test_admin_edit_during_pending_overwrites_canonical_only[chromium] - AssertionError: admin edit applied to description
assert 'd0' == 'd-from-admin'
  
  - d-from-admin
  + d0
FAILED tests/e2e/test_flows.py::test_editor_pending_edit_approved_by_admin[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for get_by_text("Target Shop").first
FAILED tests/e2e/test_concurrent.py::TestInterleavedEdits::test_admin_approves_after_admin_canonical_edit[chromium] - playwright._impl._errors.TimeoutError: Locator.click: Timeout 5000ms exceeded.
Call log:
  - waiting for locator("tr").filter(has_text="Stack").first.locator("form[action*='/admin/pending/approve-edits/shop/']").locator("button[type='submit']")
FAILED tests/e2e/test_flows.py::test_pending_cascade_on_pin_approval[chromium] - AssertionError: Locator expected to be visible
Actual value: None
Error: element(s) not found 
Call log:
  - Expect "to_be_visible" with timeout 5000ms
  - waiting for get_by_text("Cascade Shop")
FAILED tests/e2e/test_concurrent.py::TestPendingBannerDisappearsAfterApprove::test_banner_gone_once_admin_approves_chain[chromium] - AssertionError: Locator expected to be visible
Actual value: None
Error: element(s) not found 
Call log:
  - Expect "to_be_visible" with timeout 5000ms
  - waiting for get_by_text("This entry has a pending edit awaiting approval.")
============ 17 failed, 367 passed, 2 warnings in 130.54s (0:02:10) ============