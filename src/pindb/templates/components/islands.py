"""
Svelte island mount points: ``div[data-island]`` + JSON props script.

The island name must match a ``frontend/islands/<name>.entry.ts``. The loader
(``static/islands/mount.js``, loaded in ``templates/base.py``) scans for
``[data-island]``, parses the sibling JSON props block, dynamically imports
the island bundle, and mounts the Svelte component. Props must be
JSON-serializable; URLs are computed server-side via ``request.url_for``,
same as existing ``application/json`` data blocks (e.g. ``#bulk-ref-data``).
"""

import json
from collections.abc import Mapping

from htpy import Element, div, script
from markupsafe import Markup


def island(
    name: str,
    *,
    props: Mapping[str, object] | None = None,
    id: str | None = None,
    class_: str | None = None,
) -> Element:
    """Render a Svelte island mount point.

    Args:
        name (str): Island name; must match a frontend/islands/<name>.entry.ts.
        props (Mapping[str, object] | None): JSON-serializable component props.
        id (str | None): Optional id for the mount div.
        class_ (str | None): Optional classes for the mount div.

    Returns:
        Element: The mount div with an embedded non-executable JSON props block.
    """
    payload: str = json.dumps(props or {}).replace("</", "<\\/")
    return div(
        data_island=name,
        id=id,
        class_=class_,
    )[
        script(
            type="application/json",
            data_island_props=True,
        )[Markup(payload)]
    ]
