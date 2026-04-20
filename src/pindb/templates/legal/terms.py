"""
htpy page and fragment builders: `templates/legal/terms.py`.
"""

from fastapi import Request
from htpy import Element, a, div, h1, h2, li, p, ul

from pindb.config import CONFIGURATION
from pindb.templates.base import html_base
from pindb.templates.legal._shared import legal_container


def _h2(text: str) -> Element:
    return h2(class_="text-lg font-semibold mt-6 mb-2 sm:text-xl")[text]


def _p(text: str) -> Element:
    return p(class_="mb-3")[text]


def _ul(items: list[str]) -> Element:
    return ul(class_="list-disc ml-6 mb-3 flex flex-col gap-1")[
        *(li[item] for item in items)
    ]


def terms_page(request: Request) -> Element:
    email: str = CONFIGURATION.contact_email
    mailto: Element = a(
        class_="text-accent hover:underline",
        href=f"mailto:{email}",
    )[email]

    return html_base(
        title="Terms of Service",
        request=request,
        body_content=legal_container(
            div[
                h1(class_="text-2xl font-bold mb-4 sm:text-3xl")["Terms of Service"],
                _h2("1. Acceptance"),
                _p(
                    "By creating an account on or otherwise using PinDB, you "
                    "agree to these Terms of Service and to our Privacy "
                    "Policy. If you do not agree, do not use the service."
                ),
                _h2("2. Account rules"),
                _ul(
                    [
                        "You must provide a truthful username and, where "
                        "supplied, a real email address you control.",
                        "Do not impersonate another person, brand, or entity.",
                        "You are responsible for any activity under your "
                        "account. Keep your credentials secure.",
                        "One person per account. Shared accounts are not permitted.",
                    ]
                ),
                _h2("3. User-submitted content"),
                _p(
                    "PinDB lets you upload images and submit catalog data "
                    "(pins, shops, artists, tags, etc.). By submitting "
                    "content you represent that:"
                ),
                _ul(
                    [
                        "You own the content, or have permission from the "
                        "rights holder to upload it for the purpose of "
                        "cataloguing.",
                        "Your submission does not infringe any copyright, "
                        "trademark, trade secret, right of publicity, or "
                        "other right of any person or entity.",
                        "The content is accurate to the best of your knowledge.",
                    ]
                ),
                _p(
                    "You grant PinDB a non-exclusive, worldwide, royalty-"
                    "free licence to host, display, thumbnail, index, and "
                    "distribute the content for the purpose of operating "
                    "the catalog service. You retain all other rights. "
                    "Revoking this licence requires deleting the content or "
                    "your account."
                ),
                _h2("4. Prohibited use"),
                _ul(
                    [
                        "No illegal content or activity.",
                        "No harassment, hate speech, threats, or targeted abuse.",
                        "No malware, phishing, or attempts to compromise "
                        "the service or other users' accounts.",
                        "No automated scraping, crawling, or bulk download "
                        "outside any published API or export feature.",
                        "No content that infringes third-party intellectual property.",
                        "No content that is obscene, sexually explicit, or "
                        "unrelated to collectible pins.",
                    ]
                ),
                _h2("5. Intellectual property \u2014 trademarks and images"),
                _p(
                    "Pin images, names, set names, brand names, designs, "
                    "logos, and trademarks referenced on PinDB are the "
                    "property of their respective owners. PinDB is an "
                    "independent community cataloging service. We claim no "
                    "ownership of, affiliation with, sponsorship by, or "
                    "endorsement from any pin manufacturer, artist, shop, "
                    "rights holder, or brand listed in the catalog."
                ),
                _p(
                    "Images uploaded to the catalog are contributed by "
                    "users. PinDB does not verify the provenance of every "
                    "upload. If you are a rights holder and believe content "
                    "on this service infringes your rights, please use the "
                    "takedown process below."
                ),
                _h2("6. Copyright / DMCA takedown process"),
                _p(
                    "To report allegedly infringing content, send an email "
                    "to the address below containing:"
                ),
                _ul(
                    [
                        "Identification of the copyrighted or trademarked "
                        "work you claim has been infringed.",
                        "The specific URL(s) on PinDB where the allegedly "
                        "infringing material is located.",
                        "Your name, postal address, telephone number, and "
                        "email address.",
                        "A statement that you have a good-faith belief "
                        "that the use is not authorised by the rights "
                        "holder, its agent, or the law.",
                        "A statement, under penalty of perjury, that the "
                        "information in the notice is accurate and that "
                        "you are the rights holder or authorised to act on "
                        "the rights holder's behalf.",
                        "Your physical or electronic signature.",
                    ]
                ),
                p(class_="mb-3")["Send notices to ", mailto, "."],
                _p(
                    "We will remove or disable access to the material "
                    "promptly after receiving a valid notice and will notify "
                    "the user who submitted the content. Users may submit a "
                    "counter-notice using the same channel. Repeat "
                    "infringers will have their accounts terminated."
                ),
                _h2("7. Termination"),
                _p(
                    "You may delete your account at any time by contacting "
                    "us. We may suspend or terminate accounts that violate "
                    "these terms, at our discretion, with or without prior "
                    "notice."
                ),
                _h2("8. Disclaimer of warranties"),
                _p(
                    "The service is provided on an \u201cAS IS\u201d and "
                    "\u201cAS AVAILABLE\u201d basis, without warranties of "
                    "any kind, whether express or implied, including "
                    "merchantability, fitness for a particular purpose, "
                    "and non-infringement. We do not warrant that the "
                    "catalog is complete, accurate, or error-free."
                ),
                _h2("9. Limitation of liability"),
                _p(
                    "To the fullest extent permitted by law, PinDB and its "
                    "operators shall not be liable for any indirect, "
                    "incidental, special, consequential, or punitive "
                    "damages arising out of or relating to your use of the "
                    "service. Nothing in these terms excludes liability "
                    "that cannot lawfully be excluded."
                ),
                _h2("10. Governing law"),
                _p(
                    "These terms are governed by the laws of the "
                    "jurisdiction in which the service is operated, "
                    "without regard to conflict-of-law principles. The "
                    "operating jurisdiction will be stated here prior to "
                    "public launch."
                ),
                _h2("11. Changes"),
                _p(
                    "We may update these terms. Material changes will be "
                    "announced on the site and reflected in the \u201cLast "
                    "updated\u201d date above. Continued use after a "
                    "change constitutes acceptance."
                ),
                _h2("12. Contact"),
                p(class_="mb-3")["Questions about these terms: ", mailto, "."],
            ],
        ),
    )
