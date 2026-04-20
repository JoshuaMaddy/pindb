"""
htpy page and fragment builders: `templates/components/centered.py`.
"""

from typing import Literal

from htpy import Element, div

from pindb.templates.types import Content


def centered_div(
    content: Content,
    flex: bool = False,
    col: bool = False,
    additional_classes: str | None = None,
    content_width: Literal["default", "small"] = "default",
) -> Element:
    classes: set[str] = {
        "mx-auto",
        "my-5",
        "px-10",
        "gap-2",
    }

    if content_width == "default":
        classes.update(
            {
                "max-w-[80%]",
                "max-md:max-w-[90%]",
            }
        )
    elif content_width == "small":
        classes.add("max-w-[90ch]")

    if flex:
        classes.add("flex")

    if col:
        classes.add("flex-col")

    if additional_classes:
        classes.update(additional_classes.split(" "))

    return div(class_=" ".join(classes))[content]
