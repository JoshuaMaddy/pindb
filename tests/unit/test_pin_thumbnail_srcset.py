"""``pin_thumbnail`` URL building: same widths as storage, same URLs as ``url_for``."""

from uuid import UUID, uuid4

from starlette.requests import Request

from pindb import app
from pindb.file_handler import THUMBNAIL_SIZES
from pindb.templates.components.pins.pin_thumbnail import (
    _srcset_value,
    thumb_image_url,
)

# The component builds: ", ".join(f"{url} {w}w" for w in THUMBNAIL_SIZES)
# This test locks the contract without needing a full ASGI Request.


def test_all_storage_widths_appear_in_srcset_style_string() -> None:
    sample_url = "https://example.test/get/image/g?w="
    text = ", ".join(f"{sample_url}{w} {w}w" for w in THUMBNAIL_SIZES)
    for w in THUMBNAIL_SIZES:
        assert f"w={w}" in text
        assert f"{w}w" in text
    assert len(THUMBNAIL_SIZES) == 5


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "app": app,
            "router": app.router,
            "query_string": b"",
            "server": ("example.com", 443),
            "scheme": "https",
            "root_path": "",
        }
    )


def _url_for_reference(request: Request, guid: UUID, w: int) -> str:
    """What ``thumb_image_url`` used to do — one route reverse-lookup per call."""
    return str(request.url_for("get_image", guid=guid).include_query_params(w=w))


class TestThumbUrlMatchesUrlFor:
    """The cached-prefix builder must stay byte-identical to a real ``url_for``.

    ``thumb_image_url`` resolves the ``get_image`` route once per request and
    interpolates the guid and width itself, because doing the reverse lookup per
    image per width cost ~150ms on a full list page. That is only safe while it
    produces exactly what ``url_for`` would have; if the route ever moves or grows
    a query parameter, these assertions are what catches it.
    """

    def test_each_width_matches(self) -> None:
        guid = uuid4()
        for w in THUMBNAIL_SIZES:
            assert thumb_image_url(_request(), guid, w) == _url_for_reference(
                _request(), guid, w
            )

    def test_srcset_matches(self) -> None:
        guid = uuid4()
        expected = ", ".join(
            f"{_url_for_reference(_request(), guid, w)} {w}w" for w in THUMBNAIL_SIZES
        )
        assert _srcset_value(_request(), guid) == expected

    def test_distinct_guids_do_not_share_a_cached_url(self) -> None:
        """The per-request cache holds the URL *shape*, never a specific guid."""
        request = _request()
        first, second = uuid4(), uuid4()
        first_url = thumb_image_url(request, first, 200)
        second_url = thumb_image_url(request, second, 200)

        assert str(first) in first_url
        assert str(second) in second_url
        assert first_url != second_url

    def test_widths_are_not_shared_across_calls(self) -> None:
        request = _request()
        guid = uuid4()
        assert thumb_image_url(request, guid, 50).endswith("?w=50")
        assert thumb_image_url(request, guid, 600).endswith("?w=600")
