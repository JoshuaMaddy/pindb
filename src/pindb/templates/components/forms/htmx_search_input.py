"""
htpy page and fragment builders: `templates/components/forms/htmx_search_input.py`.
"""

from htpy import VoidElement, input


def htmx_search_input(
    url: str,
    target: str,
    placeholder: str = "Search…",
    name: str = "q",
    trigger: str = "input changed delay:300ms, search",
) -> VoidElement:
    """Search input wired to HTMX: GETs *url* on input and replaces *target* with the response."""
    return input(
        type="search",
        name=name,
        placeholder=placeholder,
        hx_get=url,
        hx_trigger=trigger,
        hx_target=target,
        hx_swap="innerHTML",
        class_="bg-lighter border border-lightest rounded px-2 py-1 text-base-text",
    )
