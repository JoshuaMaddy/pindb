"""
htpy page and fragment builders: `templates/components/footer.py`.
"""

from datetime import datetime

from htpy import Element, a, div, p
from htpy import footer as footer_el

from pindb import __version__
from pindb.config import CONFIGURATION


def footer() -> Element:
    year: int = datetime.now().year
    email: str = CONFIGURATION.contact_email

    link_cls: str = "text-pin-base-100 hover:text-accent hover:cursor-pointer"

    return footer_el(
        class_="mt-8 bg-pin-base-550 text-pin-base-100 text-sm px-5 py-6 relative z-[10] border-t border-pin-base-400"
    )[
        div(class_="max-w-5xl mx-auto flex flex-col gap-3")[
            div(
                class_="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-4"
            )[
                div(class_="flex flex-wrap gap-x-4 gap-y-1 items-center")[
                    p(class_="font-semibold")[f"\u00a9 {year} PinDB"],
                    p(class_="text-pin-base-200")[f"v{__version__}"],
                ],
                div(class_="flex flex-wrap gap-x-4 gap-y-1 items-center")[
                    a(class_=link_cls, href="/docs")["Docs"],
                    a(class_=link_cls, href="/about")["About"],
                    a(class_=link_cls, href="/privacy")["Privacy"],
                    a(class_=link_cls, href="/terms")["Terms"],
                    a(class_=link_cls, href=f"mailto:{email}")["Contact"],
                ],
            ],
            p(class_="text-pin-base-200 text-xs leading-relaxed")[
                "Pin images, names, brands, designs, and trademarks are the "
                "property of their respective owners. PinDB is a community "
                "cataloging service and claims no ownership of, affiliation "
                "with, or endorsement by any pin manufacturer, artist, or "
                "rights holder. All uploaded content is contributed by users; "
                "takedown requests may be sent to ",
                a(class_=link_cls, href=f"mailto:{email}")[email],
                ".",
            ],
        ],
    ]
