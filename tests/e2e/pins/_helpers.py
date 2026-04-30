"""HTTP helpers shared by pin e2e modules."""

from __future__ import annotations

import io
import struct
import zlib
from typing import Any

import httpx


def png_bytes(width: int = 1, height: int = 1) -> bytes:
    """A real, valid PNG (1×1 black pixel by default)."""

    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def admin_login_http(live_server: str) -> httpx.Client:
    client = httpx.Client(base_url=live_server, follow_redirects=False)
    client.post(
        "/auth/login",
        data={"username": "e2e_admin_pw", "password": "E2e-Admin-Secret-9!"},
    )
    return client


def editor_login_http(live_server: str) -> httpx.Client:
    client = httpx.Client(base_url=live_server, follow_redirects=False)
    client.post(
        "/auth/login",
        data={"username": "e2e_editor_pw", "password": "E2e-Editor-Secret-9!"},
    )
    return client


def create_pin_via_http(
    client: httpx.Client,
    *,
    name: str,
    shop_ids: list[int] | None = None,
    artist_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
) -> httpx.Response:
    files = {
        "front_image": ("front.png", io.BytesIO(png_bytes()), "image/png"),
    }
    data: dict[str, str | list[str]] = {
        "name": name,
        "acquisition_type": "single",
        "grade_names": "standard",
        "grade_prices": "",
        "currency_id": "999",
        "posts": "1",
    }
    if shop_ids:
        data["shop_ids"] = [str(s) for s in shop_ids]
    if artist_ids:
        data["artist_ids"] = [str(a) for a in artist_ids]
    if tag_ids:
        data["tag_ids"] = [str(t) for t in tag_ids]
    return client.post("/create/pin", data=data, files=files)


def create_tag_with_implications(
    client: httpx.Client,
    db_handle,
    *,
    name: str,
    implication_ids: tuple[int, ...] = (),
    category: str = "general",
) -> int:
    payload: dict[str, Any] = {"name": name, "category": category}
    if implication_ids:
        payload["implication_ids"] = [str(i) for i in implication_ids]
    response = client.post(
        "/create/tag",
        data=payload,
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200, response.text[:400]
    rows = db_handle(
        "SELECT id FROM tags WHERE name = %s",
        (name,),
    )
    assert rows, f"tag {name!r} missing after create"
    return int(rows[0][0])


def create_pin_set_http(client: httpx.Client, db_handle, *, name: str) -> int:
    response = client.post(
        "/create/pin_set",
        data={"name": name, "description": "e2e pin set"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200, response.text[:400]
    rows = db_handle("SELECT id FROM pin_sets WHERE name = %s", (name,))
    assert rows, f"pin_set {name!r} missing after create"
    return int(rows[0][0])


def build_implication_chain_length_five(
    client: httpx.Client,
    db_handle,
    prefix: str,
) -> tuple[int, tuple[str, ...]]:
    e_id = create_tag_with_implications(client, db_handle, name=f"{prefix}_e")
    d_id = create_tag_with_implications(
        client, db_handle, name=f"{prefix}_d", implication_ids=(e_id,)
    )
    c_id = create_tag_with_implications(
        client, db_handle, name=f"{prefix}_c", implication_ids=(d_id,)
    )
    b_id = create_tag_with_implications(
        client, db_handle, name=f"{prefix}_b", implication_ids=(c_id,)
    )
    a_id = create_tag_with_implications(
        client, db_handle, name=f"{prefix}_a", implication_ids=(b_id,)
    )
    names = tuple(f"{prefix}_{letter}" for letter in ("a", "b", "c", "d", "e"))
    return a_id, names
