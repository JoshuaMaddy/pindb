from htpy import BaseElement, Element, div, label


def form_field(
    label_text: str,
    field_id: str,
    child: BaseElement,
) -> Element:
    """Labeled form field: flex-col wrapper with a bold label above an input/textarea/select."""
    return div(class_="flex flex-col gap-1")[
        label(for_=field_id, class_="font-semibold")[label_text],
        child,
    ]
