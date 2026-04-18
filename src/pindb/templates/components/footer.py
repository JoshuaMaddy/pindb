from datetime import datetime

from htpy import Element, a, div, p
from htpy import footer as footer_el

from pindb import __version__
from pindb.config import CONFIGURATION


def footer() -> Element:
    year: int = datetime.now().year
    email: str = CONFIGURATION.contact_email

    link_cls: str = "no-underline text-pin-base-100 hover:text-accent"

    return footer_el(class_="mt-8 bg-pin-base-600 text-pin-base-100 text-sm px-5 py-6")[
        div(class_="max-w-5xl mx-auto flex flex-col gap-3")[
            div(class_="flex flex-wrap gap-4 items-center")[
                p(class_="font-semibold")[f"\u00a9 {year} PinDB"],
                p(class_="text-pin-base-200")[f"v{__version__}"],
                div(class_="flex gap-4 ml-auto")[
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
