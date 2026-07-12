"""The display share card — the thing that unfurls when a link is pasted."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from pindb.og_image import _cover_fit, _cover_fit_rect, build_user_display_og_image

_OG_SIZE = (1200, 630)


def _photo(width: int, height: int, color=(200, 30, 40)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _decode(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


@pytest.mark.unit
class TestCoverFit:
    @pytest.mark.parametrize(
        "source", [(400, 1600), (1600, 400), (1200, 630), (37, 41)]
    )
    def test_rect_always_fills_the_frame(self, source):
        with Image.open(io.BytesIO(_photo(*source))) as src:
            assert _cover_fit_rect(src, *_OG_SIZE).size == _OG_SIZE

    def test_square_helper_still_squares(self):
        """`_cover_fit` now delegates to the rect version; keep it square."""
        with Image.open(io.BytesIO(_photo(800, 200))) as src:
            assert _cover_fit(src, 252).size == (252, 252)


@pytest.mark.unit
class TestDisplayOgCard:
    def test_renders_with_a_cover_photo(self):
        card = _decode(
            build_user_display_og_image(
                cover_image_bytes=_photo(1600, 900),
                username="josh",
                title="My Shadow Box",
            )
        )
        assert card.size == _OG_SIZE
        assert card.format == "WEBP"

    def test_falls_back_when_there_is_no_cover(self):
        """An empty display still has to share as *something*."""
        card = _decode(
            build_user_display_og_image(cover_image_bytes=None, username="josh")
        )
        assert card.size == _OG_SIZE
        assert card.format == "WEBP"

    def test_undecodable_cover_falls_back_instead_of_raising(self):
        card = _decode(
            build_user_display_og_image(
                cover_image_bytes=b"not an image at all", username="josh"
            )
        )
        assert card.size == _OG_SIZE

    def test_scrim_darkens_the_photo_under_the_text(self):
        """The card overlays text on an arbitrary photo; without the scrim it is
        unreadable against a bright one."""
        white = _photo(1600, 900, color=(255, 255, 255))
        card = _decode(build_user_display_og_image(white, "josh")).convert("RGB")

        def luminance(xy: tuple[int, int]) -> int:
            pixel = card.getpixel(xy)
            assert isinstance(pixel, tuple)
            return int(pixel[0]) + int(pixel[1]) + int(pixel[2])

        # Bottom-left, where the "@josh's pin display" line sits.
        bottom = luminance((20, _OG_SIZE[1] - 20))
        top_middle = luminance((600, 300))
        assert bottom < top_middle, "the bottom band must be the darker one"
        assert top_middle < 255 * 3, "the flat scrim must dim the frame overall"
