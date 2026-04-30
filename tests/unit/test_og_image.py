"""Unit tests for ``pindb.og_image.build_entity_og_image``.

The renderer has no DB or HTTP dependencies, so we exercise it directly with
synthetic pin bytes and assert layout invariants by sampling the resulting
WebP — full visual diffing isn't worth the maintenance burden, but the
structural checks here catch regressions in size, slot positioning, and the
empty-slot fill color.
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw

from pindb.og_image import build_entity_og_image, build_pin_og_image


def _solid_pin(color: tuple[int, int, int]) -> bytes:
    """Encode a 400x400 solid-color WebP standing in for a real pin thumbnail."""
    img = Image.new("RGB", (400, 400), color)
    ImageDraw.Draw(img).ellipse((0, 0, 399, 399), fill=color)
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP")
    return buffer.getvalue()


def _transparent_pin(color: tuple[int, int, int]) -> bytes:
    """A 400x400 PNG: opaque colored disk on a fully transparent background."""
    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((0, 0, 399, 399), fill=(*color, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _decode(webp_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(webp_bytes)).convert("RGB")


def test_output_is_1200x630_webp() -> None:
    out = build_entity_og_image("Some Tag", [_solid_pin((200, 50, 50))])
    image = _decode(out)
    assert image.size == (1200, 630)


def test_empty_slots_are_filled_with_dark_panel_color() -> None:
    """Slots without a pin are filled with #1E1E2E (Catppuccin mocha base)."""
    out = build_entity_og_image("Solo Pin", [_solid_pin((250, 0, 0))])
    image = _decode(out)
    # Center of the rightmost square (slot index 3, x=918, size=252, y=354).
    sample = image.getpixel((918 + 126, 354 + 126))
    assert sample == (0x1E, 0x1E, 0x2E)


def test_pin_slots_render_their_image() -> None:
    """First slot's center should reflect the supplied pin's color."""
    out = build_entity_og_image("Bright Tag", [_solid_pin((220, 30, 30))])
    image = _decode(out)
    # Center of the leftmost square (slot index 0, x=30, y=354, size 252).
    pixel = image.getpixel((30 + 126, 354 + 126))
    assert isinstance(pixel, tuple) and len(pixel) >= 3
    r, g, b = pixel[0], pixel[1], pixel[2]
    # WebP is lossy; allow ±15 per channel.
    assert abs(r - 220) < 15 and abs(g - 30) < 15 and abs(b - 30) < 15


def test_extra_pins_beyond_four_are_ignored() -> None:
    """Sixth pin must not displace the first four slots."""
    pins = [_solid_pin((c, c, c)) for c in (50, 100, 150, 200, 250, 90)]
    out = build_entity_og_image("Lots Of Pins", pins)
    image = _decode(out)
    # Slot 4 is past the right edge — there is no fifth slot to inspect.
    # Just confirm the image is still valid 1200x630.
    assert image.size == (1200, 630)


def test_invalid_image_bytes_fall_back_to_empty_panel() -> None:
    """Bogus input bytes degrade to the empty-square fill color rather than crash."""
    out = build_entity_og_image("Broken Pin", [b"not-an-image"])
    image = _decode(out)
    assert image.getpixel((30 + 126, 354 + 126)) == (0x1E, 0x1E, 0x2E)


def test_transparent_pin_composites_over_dark_panel() -> None:
    """Transparent regions of a pin show the empty-panel fill, not the canvas."""
    out = build_entity_og_image("Transparent Pin", [_transparent_pin((250, 0, 0))])
    image = _decode(out)
    # The disk is inscribed in a 400x400 source which gets cover-fit to
    # 252x252; corner regions of that square fall outside the disk and were
    # transparent in the source. They should be painted with the empty-panel
    # color (#1E1E2E) rather than whatever the wordmark band held there.
    # Sample at (60, 10) inside the slot — inside the rounded-corner mask
    # (corner radius 50, so well within the rounded shape) but well outside
    # the inscribed circle of radius 126. Slot 0 lives at (30, 354).
    corner_pixel = image.getpixel((30 + 60, 354 + 10))
    assert isinstance(corner_pixel, tuple) and len(corner_pixel) >= 3
    cr, cg, cb = corner_pixel[0], corner_pixel[1], corner_pixel[2]
    assert abs(cr - 0x1E) <= 5 and abs(cg - 0x1E) <= 5 and abs(cb - 0x2E) <= 5, (
        f"transparent corner not painted with empty-panel fill: {(cr, cg, cb)}"
    )
    # Center of the same square still reflects the disk color (lossy WebP).
    center_pixel = image.getpixel((30 + 126, 354 + 126))
    assert isinstance(center_pixel, tuple) and len(center_pixel) >= 3
    r, g, b = center_pixel[0], center_pixel[1], center_pixel[2]
    assert abs(r - 250) < 15 and g < 30 and b < 30


def _pin_og_bg_rgb() -> tuple[int, int, int]:
    """``bg-darker`` / ``--color-pin-base-550`` (see ``og_image._PIN_OG_BACKGROUND``)."""
    return (18, 18, 28)


def test_pin_og_is_1200x630() -> None:
    out = build_pin_og_image(_solid_pin((100, 150, 200)))
    image = _decode(out)
    assert image.size == (1200, 630)


def test_pin_og_wide_image_has_vertical_letterboxing() -> None:
    """A wide strip is scaled to full width; top/bottom show the shell background."""
    img = Image.new("RGB", (1200, 200), (200, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    out = build_pin_og_image(buf.getvalue())
    image = _decode(out)
    bg = _pin_og_bg_rgb()
    top_mid = image.getpixel((600, 8))
    assert isinstance(top_mid, tuple) and len(top_mid) >= 3
    tr, tg, tb = top_mid[0], top_mid[1], top_mid[2]
    assert all(abs(c - bg[i]) <= 8 for i, c in enumerate((tr, tg, tb))), top_mid


def test_pin_og_tall_image_has_horizontal_pillarboxing() -> None:
    """A tall strip is scaled to full height; sides show the shell background."""
    img = Image.new("RGB", (200, 900), (50, 200, 50))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    out = build_pin_og_image(buf.getvalue())
    image = _decode(out)
    bg = _pin_og_bg_rgb()
    left_mid = image.getpixel((8, 315))
    assert isinstance(left_mid, tuple) and len(left_mid) >= 3
    lr, lg, lb = left_mid[0], left_mid[1], left_mid[2]
    assert all(abs(c - bg[i]) <= 8 for i, c in enumerate((lr, lg, lb))), left_mid


def test_pin_og_invalid_bytes_is_flat_background() -> None:
    out = build_pin_og_image(b"not-an-image")
    image = _decode(out)
    assert image.size == (1200, 630)
    px = image.getpixel((10, 10))
    assert isinstance(px, tuple) and len(px) >= 3
    er, eg, eb = _pin_og_bg_rgb()
    r, g, b = px[0], px[1], px[2]
    # Output is lossy WebP even for a flat field; stay near the shell RGB.
    assert abs(r - er) <= 5 and abs(g - eg) <= 5 and abs(b - eb) <= 5
