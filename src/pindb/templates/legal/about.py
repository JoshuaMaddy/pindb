from fastapi import Request
from htpy import Element, a, div, h1, h2, li, p, ul

from pindb import __version__
from pindb.config import CONFIGURATION
from pindb.templates.base import html_base
from pindb.templates.legal._shared import legal_container


def about_page(request: Request) -> Element:
    email: str = CONFIGURATION.contact_email
    return html_base(
        title="About",
        request=request,
        body_content=legal_container(
            div[
                h1(class_="text-2xl font-bold mb-2 sm:text-3xl")["About PinDB"],
                p(class_="text-pin-base-200 mb-6")[f"Version {__version__}"],
                h2(class_="text-lg font-semibold mt-6 mb-2 sm:text-xl")[
                    "What is PinDB?"
                ],
                p(class_="mb-4")[
                    "PinDB is a community-run catalog for collectible pins. "
                    "Users can browse, search, and track pin sets, artists, "
                    "shops, and tags. Accounts let you mark favorites, "
                    "record what you own, and list what you want or have "
                    "available to trade."
                ],
                h2(class_="text-lg font-semibold mt-6 mb-2 sm:text-xl")["How it works"],
                p(class_="mb-4")[
                    "Editors and administrators curate the catalog. New "
                    "entries submitted by editors enter a pending queue and "
                    "become publicly visible once an administrator approves "
                    "them. All changes are recorded in an audit log so "
                    "history is preserved."
                ],
                h2(class_="text-lg font-semibold mt-6 mb-2 sm:text-xl")[
                    "Who runs this service?"
                ],
                p(class_="mb-4")[
                    "PinDB is operated as a hobby project. It is not "
                    "affiliated with, endorsed by, or sponsored by any pin "
                    "manufacturer, artist, shop, or brand referenced in the "
                    "catalog."
                ],
                h2(class_="text-lg font-semibold mt-6 mb-2 sm:text-xl")[
                    "Getting in touch"
                ],
                p(class_="mb-2")[
                    "For any of the following, contact ",
                    a(
                        class_="text-accent hover:underline",
                        href=f"mailto:{email}",
                    )[email],
                    ":",
                ],
                ul(class_="list-disc ml-6 mb-4 flex flex-col gap-1")[
                    li["Account questions or deletion requests"],
                    li["Privacy and data requests"],
                    li["Copyright / trademark takedown notices"],
                    li["Bug reports and feature suggestions"],
                    li["General feedback"],
                ],
                h2(class_="text-lg font-semibold mt-6 mb-2 sm:text-xl")[
                    "Related pages"
                ],
                ul(class_="list-disc ml-6 flex flex-col gap-1")[
                    li[
                        a(class_="text-accent hover:underline", href="/privacy")[
                            "Privacy Policy"
                        ]
                    ],
                    li[
                        a(class_="text-accent hover:underline", href="/terms")[
                            "Terms of Service"
                        ]
                    ],
                ],
            ],
        ),
    )
