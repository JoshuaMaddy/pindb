from htpy import Element, VoidElement, div


def centered_div(content: Element | list[Element | VoidElement]) -> Element:
    return div(class_="w-[60ch] mx-auto my-5")[content]
