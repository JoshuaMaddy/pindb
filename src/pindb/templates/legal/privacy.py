from fastapi import Request
from htpy import Element, a, code, div, h1, h2, li, p, ul

from pindb.config import CONFIGURATION
from pindb.templates.base import html_base
from pindb.templates.legal._shared import legal_container


def _h2(text: str) -> Element:
    return h2(class_="text-xl font-semibold mt-6 mb-2")[text]


def _p(text: str) -> Element:
    return p(class_="mb-3")[text]


def _ul(items: list[str | Element]) -> Element:
    return ul(class_="list-disc ml-6 mb-3 flex flex-col gap-1")[
        *(li[item] for item in items)
    ]


def privacy_page(request: Request) -> Element:
    email: str = CONFIGURATION.contact_email
    mailto: Element = a(
        class_="text-accent hover:underline",
        href=f"mailto:{email}",
    )[email]

    return html_base(
        title="Privacy Policy",
        request=request,
        body_content=legal_container(
            div[
                h1(class_="text-3xl font-bold mb-4")["Privacy Policy"],
                _h2("1. Who we are"),
                p(class_="mb-3")[
                    "PinDB is a community-run catalog of collectible pins. "
                    "For any privacy-related enquiry, contact ",
                    mailto,
                    ".",
                ],
                _h2("2. Data we collect"),
                _p(
                    "We keep only the data required to operate the service. "
                    "We do not sell personal data and we do not share it "
                    "with advertisers."
                ),
                p(class_="font-semibold mt-3")["Account data"],
                _ul(
                    [
                        "Username (required, unique, chosen by you)",
                        "Email address (optional unless required by your "
                        "OAuth provider)",
                        "Password hash (Argon2, irreversible — we never see "
                        "or store your plaintext password)",
                        "UI theme preference",
                        "Editor / administrator role flags",
                    ]
                ),
                p(class_="font-semibold mt-3")["OAuth identity data"],
                _p(
                    "If you sign in with Google, Discord, or Meta (Facebook "
                    "Login), we receive and store the provider name, the "
                    "provider's stable user ID, the email address on that "
                    "account, the display name, and whether the provider "
                    "reports the email as verified."
                ),
                p(class_="font-semibold mt-3")["Session data"],
                _p(
                    "When you sign in we generate a random session token, "
                    "store a hashed reference in our database, and set it "
                    "as an HttpOnly cookie on your browser. Sessions expire "
                    "after 30 days."
                ),
                p(class_="font-semibold mt-3")["Audit log"],
                _p(
                    "Every create / update / delete action performed on "
                    "catalog entities is recorded with the acting user's "
                    "ID, a timestamp, and a JSON patch of the changed "
                    "fields. This log is retained indefinitely for "
                    "accountability and rollback."
                ),
                p(class_="font-semibold mt-3")["Uploaded images"],
                _p(
                    "Pin images you upload are stored by a random UUID. "
                    "EXIF and other embedded metadata (including camera "
                    "GPS coordinates) are stripped on ingest. A 256 px "
                    "WebP thumbnail is generated at the same time."
                ),
                _h2("3. Data we do NOT collect"),
                _ul(
                    [
                        "No IP address logging in the application layer",
                        "No user-agent or device fingerprinting",
                        "No analytics (Google Analytics, Plausible, Mixpanel, etc.)",
                        "No advertising or tracking pixels",
                        "No third-party JavaScript beyond the functional "
                        "libraries listed in §5",
                    ]
                ),
                _h2("4. Cookies"),
                _p(
                    "All cookies we set are strictly necessary. No consent banner is required."
                ),
                _ul(
                    [
                        div[
                            code["session"],
                            " \u2014 primary authentication token. HttpOnly, "
                            "SameSite=Lax, 30-day expiry.",
                        ],
                        div[
                            code["pindb_starlette_session"],
                            " \u2014 session-scoped cookie used by the OAuth "
                            "library (Authlib) to carry state between the "
                            "redirect to a provider and the return callback.",
                        ],
                        div[
                            code["pindb_oauth_onboarding"],
                            " \u2014 short-lived (10 minute) cookie that holds "
                            "the OAuth identity between sign-in and new "
                            "account creation.",
                        ],
                        div[
                            code["pindb_oauth_link"],
                            " \u2014 short-lived (10 minute) cookie used when "
                            "linking an additional OAuth provider to your "
                            "existing account.",
                        ],
                    ]
                ),
                _h2("5. Third parties and data processors"),
                _ul(
                    [
                        "Google, Discord, Meta \u2014 only if you choose to "
                        "sign in with them. See their respective privacy "
                        "policies.",
                        "Cloudflare R2 \u2014 object storage for uploaded pin "
                        "images (optional backend; may be filesystem in "
                        "self-hosted deployments).",
                        "Meilisearch \u2014 self-hosted search index. Holds "
                        "catalog data only, no user PII.",
                        "PostgreSQL \u2014 self-hosted primary database.",
                    ]
                ),
                _h2("6. Legal basis (GDPR Article 6)"),
                _ul(
                    [
                        "Performance of contract \u2014 maintaining your "
                        "account and letting you use the service.",
                        "Legitimate interest \u2014 keeping an audit log to "
                        "protect catalog integrity and prevent abuse.",
                        "Consent \u2014 when you link an OAuth provider or "
                        "optionally provide an email address.",
                    ]
                ),
                _h2("7. Your rights"),
                _p(
                    "Under the GDPR, UK GDPR, and CCPA you have the "
                    "following rights, which we honour regardless of where "
                    "you live:"
                ),
                _ul(
                    [
                        "Access \u2014 request a copy of your personal data.",
                        "Rectification \u2014 correct inaccurate data.",
                        "Erasure \u2014 delete your account and associated "
                        "data. Audit-log references will be anonymised.",
                        "Portability \u2014 receive your data in a machine-"
                        "readable format.",
                        "Objection / restriction \u2014 limit certain processing.",
                        "Complaint \u2014 lodge a complaint with your local "
                        "data protection authority.",
                    ]
                ),
                p(class_="mb-3")[
                    "To exercise any of these rights, email ",
                    mailto,
                    ". We respond within 30 days.",
                ],
                _h2("8. Retention"),
                _ul(
                    [
                        "Session tokens \u2014 30 days from creation.",
                        "Temporary OAuth cookies \u2014 10 minutes.",
                        "Account data \u2014 until you request deletion.",
                        "Audit log \u2014 retained indefinitely; user ID "
                        "references are anonymised on account deletion.",
                        "Uploaded images \u2014 until you or an admin delete "
                        "the corresponding pin.",
                    ]
                ),
                _h2("9. Children"),
                _p(
                    "PinDB is not intended for anyone under 16. We do not "
                    "knowingly collect data from children. If you believe a "
                    "child has created an account, please contact us and we "
                    "will remove it."
                ),
                _h2("10. Security and breach notification"),
                _p(
                    "Passwords are hashed with Argon2. Session cookies are "
                    "HttpOnly and SameSite=Lax. In the event of a personal-"
                    "data breach that is likely to result in a risk to your "
                    "rights, we will notify affected users without undue "
                    "delay and, where required, within 72 hours."
                ),
                _h2("11. Changes to this policy"),
                _p(
                    "Material changes will be announced on the site and "
                    "reflected in the \u201cLast updated\u201d date above. "
                    "Continued use of the service after a change "
                    "constitutes acceptance."
                ),
                _h2("12. Contact"),
                p(class_="mb-3")["Privacy enquiries: ", mailto, "."],
            ],
        ),
    )
