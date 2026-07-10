"""Phase G: Swiper/SortableJS vendored — no runtime CDN loads, CSP tightened."""

from __future__ import annotations

import httpx


class TestVendoredLibs:
    def test_pin_carousel_boots_from_vendored_swiper(
        self, admin_browser_context, live_server, make_pin
    ):
        pin = make_pin("SwiperPin", tag_names=["swiper-tag"])
        page = admin_browser_context.new_page()
        external: list[str] = []
        page.on(
            "request",
            lambda request: (
                external.append(request.url)
                if not request.url.startswith(live_server)
                else None
            ),
        )
        page.goto(f"{live_server}/get/pin/{pin['id']}", wait_until="networkidle")

        page.wait_for_function(
            """() => {
                const el = document.querySelector('.pin-swiper-main');
                return el && el.classList.contains('swiper-initialized');
            }""",
            timeout=10_000,
        )
        cdn_hits = [url for url in external if "jsdelivr" in url or "unpkg" in url]
        assert cdn_hits == [], f"unexpected CDN requests: {cdn_hits}"

    def test_csp_has_no_cdn_hosts(self, live_server):
        response = httpx.get(f"{live_server}/")
        csp = response.headers.get("content-security-policy-report-only", "")
        assert csp, "CSP report-only header missing"
        assert "jsdelivr" not in csp
        assert "unpkg" not in csp
