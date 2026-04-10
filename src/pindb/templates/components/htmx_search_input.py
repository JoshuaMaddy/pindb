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
        type_="search",
        name=name,
        placeholder=placeholder,
        hx_get=url,
        hx_trigger=trigger,
        hx_target=target,
        hx_swap="innerHTML",
        class_="bg-pin-base-450 border border-pin-base-400 rounded px-3 py-1 text-pin-base-text",
    )
