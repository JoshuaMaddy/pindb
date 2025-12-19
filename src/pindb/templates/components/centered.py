from htpy import Element, Fragment, VoidElement, div


def centered_div(
    content: Element
    | VoidElement
    | None
    | Fragment
    | list[Element | VoidElement | None | Fragment],
    wide: bool = False,
    flex: bool = False,
    col: bool = False,
    gap: int = 2,
    class_: str | None = None,
) -> Element:
    classes: set[str] = {"mx-auto", "my-5", "px-10", f"gap-{gap}"}

    if flex:
        classes.add("flex")

    if col:
        classes.add("flex-col")

    if wide:
        classes.add("max-w-[120ch]")
    else:
        classes.add("max-w-[80ch]")

    if class_:
        classes.update(class_.split(" "))

    return div(class_=" ".join(classes))[content]
