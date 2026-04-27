"""
htpy page and fragment builders: `templates/legal/_shared.py`.
"""

from htpy import Element, div

from pindb.templates.types import Content


def legal_container(inner: Content) -> Element:
    return div(class_="w-full max-w-3xl mx-auto mt-5 px-5 pb-8 text-pin-base-text")[
        inner,
    ]
