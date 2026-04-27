"""
htpy page and fragment builders: `templates/components/form_field.py`.
"""

from htpy import BaseElement, Element, div, label, span


def form_field(
    label_text: str,
    field_id: str,
    child: BaseElement,
    required: bool = False,
) -> Element:
    """Labeled form field: flex-col wrapper with a bold label above an input/textarea/select."""
    label_content: list[str | Element] = [label_text]
    if required:
        label_content.append(span(class_="text-error-main ml-0.5")["*"])
    return div(class_="flex flex-col gap-1")[
        label(for_=field_id, class_="font-semibold")[label_content],
        child,
    ]
