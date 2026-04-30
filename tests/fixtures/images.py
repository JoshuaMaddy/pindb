"""Binary fixtures for image uploads in integration tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def png_bytes() -> bytes:
    """A valid 1×1 PNG byte string, PIL can open it."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def png_upload(png_bytes: bytes):
    """Tuple suitable for TestClient files={"front_image": png_upload}."""
    return ("test.png", png_bytes, "image/png")
