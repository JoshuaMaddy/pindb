"""Open Graph / Twitter card image generator for entity and pin pages.

**Entity** (tag / shop / artist / pin_set) cards are a 1200x630 WebP composed on
``static/media/opengraph-image-blank.webp`` (includes the "PinDB" wordmark):
the entity name in Roboto Bold below the wordmark, and up to four square pin
thumbnails along the bottom. Empty slots use ``#1E1E2E``.

**Pin** cards use the same canvas size with the site ``bg-darker`` fill and the
front image ``contain``-fitted and centered.

Both the blank base and the Roboto Bold TTF live under tracked paths in
``static/`` (``static/media/`` and ``static/fonts/``). They sit inside
``static/`` to ride along with the existing static-asset bundling, but they
are never referenced by the browser — Pillow loads them from the filesystem
on the server. Avoid putting them under ``static/vendor/`` because that
directory is wiped and rebuilt by ``npm run vendor:build`` from npm packages.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageChops, ImageDraw, ImageFont

_STATIC_DIR: Path = Path(__file__).resolve().parent / "static"
_BLANK_TEMPLATE_PATH: Path = _STATIC_DIR / "media" / "opengraph-image-blank.webp"
_FONT_PATH: Path = _STATIC_DIR / "fonts" / "Roboto-Bold.ttf"

# Layout constants (image is 1200x630).
_IMAGE_SIZE: tuple[int, int] = (1200, 630)
# Catppuccin mocha "base" — also the requested fallback for empty pin slots.
_EMPTY_SQUARE_FILL: tuple[int, int, int] = (0x1E, 0x1E, 0x2E)
# ``bg-darker`` / ``--color-pin-base-550`` from ``static/input.css`` (mocha default).
_PIN_OG_BACKGROUND: tuple[int, int, int] = (18, 18, 28)
# Catppuccin mocha "text" — softer than pure white, matches the rest of the UI.
_TITLE_TEXT_FILL: tuple[int, int, int] = (0xCD, 0xD6, 0xF4)

_SQUARE_SIZE: int = 252
_SQUARE_Y: int = 354
_SQUARE_X_POSITIONS: tuple[int, int, int, int] = (30, 326, 622, 918)
# ~20% of the square's width.
_SQUARE_CORNER_RADIUS: int = 50

# User list OG cards: 2×4 grid of thumbnails, no text, plain dark background.
# Same square size and x-positions as entity cards; two rows fit in 630px with
# 30px outer margin (top/bottom) and 66px gap between rows.
_USER_GRID_ROW_Y: tuple[int, int] = (30, 348)  # 30 + 252 + 66 = 348; 348+252+30=630

# The "PinDB" wordmark on the base ends near y=156; leave a small gap, then
# vertically center the entity-name text in the band above the squares.
_TITLE_BAND_TOP: int = 168
_TITLE_BAND_BOTTOM: int = _SQUARE_Y - 16  # 338
_TITLE_MAX_WIDTH: int = 1100
_TITLE_INITIAL_FONT_SIZE: int = 96
_TITLE_MIN_FONT_SIZE: int = 40
_TITLE_FONT_STEP: int = 4


@lru_cache(maxsize=1)
def _blank_template() -> Image.Image:
    """Load the prebuilt 1200x630 base image once per process."""
    return Image.open(_BLANK_TEMPLATE_PATH).convert("RGB")


@lru_cache(maxsize=32)
def _title_font(size: int) -> ImageFont.FreeTypeFont:
    """Cache ``ImageFont`` instances keyed by pixel size."""
    return ImageFont.truetype(str(_FONT_PATH), size=size)


def _fit_title(
    draw: ImageDraw.ImageDraw, text: str
) -> tuple[ImageFont.FreeTypeFont, str]:
    """Pick the largest font size that keeps *text* within ``_TITLE_MAX_WIDTH``.

    Falls back to ellipsizing at the minimum supported size when even that
    doesn't fit (very long entity names).
    """
    for size in range(
        _TITLE_INITIAL_FONT_SIZE, _TITLE_MIN_FONT_SIZE - 1, -_TITLE_FONT_STEP
    ):
        font = _title_font(size)
        width = draw.textlength(text, font=font)
        if width <= _TITLE_MAX_WIDTH:
            return font, text
    font = _title_font(_TITLE_MIN_FONT_SIZE)
    truncated = text
    while truncated and draw.textlength(truncated + "…", font=font) > _TITLE_MAX_WIDTH:
        truncated = truncated[:-1]
    return font, (truncated + "…") if truncated else text[: max(1, len(text))]


def _draw_title(canvas: Image.Image, name: str) -> None:
    """Render *name* centered horizontally in the title band on *canvas*."""
    draw = ImageDraw.Draw(canvas)
    font, display_text = _fit_title(draw, name)
    bbox = draw.textbbox((0, 0), display_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (canvas.width - text_width) // 2 - bbox[0]
    band_height = _TITLE_BAND_BOTTOM - _TITLE_BAND_TOP
    y = _TITLE_BAND_TOP + (band_height - text_height) // 2 - bbox[1]
    draw.text((x, y), display_text, fill=_TITLE_TEXT_FILL, font=font)


def _rounded_square_mask(size: int, radius: int) -> Image.Image:
    """Build an alpha mask for a square with rounded corners."""
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255
    )
    return mask


@lru_cache(maxsize=4)
def _square_mask_cached(size: int, radius: int) -> Image.Image:
    return _rounded_square_mask(size, radius)


def _cover_fit(image: Image.Image, size: int) -> Image.Image:
    """Resize *image* to ``size x size`` using object-fit-cover semantics.

    Preserves an alpha channel when the source has one — pin art is sometimes
    die-cut against a transparent background, and we want those holes to
    stay transparent so the caller can lay them over the dark "empty" panel.
    """
    has_alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
    src = image.convert("RGBA" if has_alpha else "RGB")
    src_w, src_h = src.size
    scale = max(size / src_w, size / src_h)
    new_w = max(size, int(round(src_w * scale)))
    new_h = max(size, int(round(src_h * scale)))
    resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - size) // 2
    top = (new_h - size) // 2
    return resized.crop((left, top, left + size, top + size))


def _empty_square(size: int) -> Image.Image:
    return Image.new("RGB", (size, size), _EMPTY_SQUARE_FILL)


def _paste_square(canvas: Image.Image, square: Image.Image, x: int, y: int) -> None:
    """Stamp *square* onto *canvas* with rounded-corner alpha clipping.

    When *square* has an alpha channel, paint the dark empty-panel fill
    underneath first so transparent regions of the pin show that fill rather
    than the wordmark band bleeding through.
    """
    rounded = _square_mask_cached(square.width, _SQUARE_CORNER_RADIUS)
    if square.mode == "RGBA":
        background = _empty_square(square.width)
        canvas.paste(background, (x, y), rounded)
        alpha = square.split()[3]
        combined = ImageChops.multiply(alpha, rounded)
        canvas.paste(square.convert("RGB"), (x, y), combined)
        return
    canvas.paste(square, (x, y), rounded)


def _contain_fit_within(image: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize *image* so it fits entirely inside ``max_w`` x ``max_h`` (object-fit: contain).

    Preserves alpha when present. Does not mutate the source.
    """
    has_alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
    src = image.convert("RGBA" if has_alpha else "RGB")
    src_w, src_h = src.size
    if src_w <= 0 or src_h <= 0:
        return src
    scale = min(max_w / src_w, max_h / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    return src.resize((new_w, new_h), Image.Resampling.LANCZOS)


def build_pin_og_image(pin_image_bytes: bytes) -> bytes:
    """Render a 1200x630 share image: pin art contain-fit on the app shell background.

    The background matches the default theme ``bg-darker`` surface (purple-gray).
    The pin is scaled with ``contain`` semantics inside the full OG rectangle
    (standard 1.91:1 bounds) and centered.

    Args:
        pin_image_bytes: Raw bytes for the pin's front image (any supported format).

    Returns:
        Encoded WebP bytes (1200x630, sRGB). On decode failure, a flat background
        image is returned so callers can still emit a valid response.
    """
    w, h = _IMAGE_SIZE
    canvas = Image.new("RGB", (w, h), _PIN_OG_BACKGROUND)
    try:
        with Image.open(io.BytesIO(pin_image_bytes)) as src:
            fitted = _contain_fit_within(src, w, h)
    except (OSError, ValueError):
        buffer = io.BytesIO()
        canvas.save(buffer, format="WEBP", quality=85, method=4)
        return buffer.getvalue()

    fw, fh = fitted.size
    x0 = (w - fw) // 2
    y0 = (h - fh) // 2
    if fitted.mode == "RGBA":
        canvas.paste(fitted, (x0, y0), fitted)
    else:
        canvas.paste(fitted, (x0, y0))

    buffer = io.BytesIO()
    canvas.save(buffer, format="WEBP", quality=85, method=4)
    return buffer.getvalue()


def build_user_list_og_image(pin_image_bytes: Sequence[bytes]) -> bytes:
    """Render a 2×4 thumbnail grid OG card for user pin list pages.

    Args:
        pin_image_bytes: Raw bytes for up to eight representative pin images.
            Extras are ignored; missing slots are filled with ``#1E1E2E``.

    Returns:
        Encoded WebP bytes (1200x630, sRGB).
    """
    w, h = _IMAGE_SIZE
    canvas = Image.new("RGB", (w, h), _EMPTY_SQUARE_FILL)

    slot = 0
    for y in _USER_GRID_ROW_Y:
        for x in _SQUARE_X_POSITIONS:
            if slot < len(pin_image_bytes):
                try:
                    with Image.open(io.BytesIO(pin_image_bytes[slot])) as src:
                        square = _cover_fit(src, _SQUARE_SIZE)
                except (OSError, ValueError):
                    square = _empty_square(_SQUARE_SIZE)
            else:
                square = _empty_square(_SQUARE_SIZE)
            _paste_square(canvas, square, x, y)
            slot += 1

    buffer = io.BytesIO()
    canvas.save(buffer, format="WEBP", quality=85, method=4)
    return buffer.getvalue()


def build_entity_og_image(name: str, pin_image_bytes: Sequence[bytes]) -> bytes:
    """Render the OG card for an entity and return WebP bytes.

    Args:
        name: Entity display name. Drawn under the "PinDB" wordmark; auto-shrunk
            and ellipsized if it would overflow the title band.
        pin_image_bytes: Raw bytes for up to four representative pin images.
            Extras are ignored; missing slots are filled with ``#1E1E2E``.

    Returns:
        Encoded WebP bytes (1200x630, sRGB).
    """
    canvas = _blank_template().copy()
    _draw_title(canvas, name)

    for slot_index, x in enumerate(_SQUARE_X_POSITIONS):
        if slot_index < len(pin_image_bytes):
            try:
                with Image.open(io.BytesIO(pin_image_bytes[slot_index])) as src:
                    square = _cover_fit(src, _SQUARE_SIZE)
            except (OSError, ValueError):
                square = _empty_square(_SQUARE_SIZE)
        else:
            square = _empty_square(_SQUARE_SIZE)
        _paste_square(canvas, square, x, _SQUARE_Y)

    buffer = io.BytesIO()
    canvas.save(buffer, format="WEBP", quality=85, method=4)
    return buffer.getvalue()
