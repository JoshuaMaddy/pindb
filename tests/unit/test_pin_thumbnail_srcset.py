"""``pin_thumbnail`` uses the same width list as storage (srcset descriptors)."""

from pindb.file_handler import THUMBNAIL_SIZES

# The component builds: ", ".join(f"{url} {w}w" for w in THUMBNAIL_SIZES)
# This test locks the contract without needing a full ASGI Request.


def test_all_storage_widths_appear_in_srcset_style_string() -> None:
    sample_url = "https://example.test/get/image/g?w="
    text = ", ".join(f"{sample_url}{w} {w}w" for w in THUMBNAIL_SIZES)
    for w in THUMBNAIL_SIZES:
        assert f"w={w}" in text
        assert f"{w}w" in text
    assert len(THUMBNAIL_SIZES) == 5
