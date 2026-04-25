"""Small shared helpers: time, URLs, and currency display."""

from datetime import datetime, timezone
from urllib.parse import ParseResult, urlparse

from babel.numbers import format_currency


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime (no ``tzinfo``).

    Returns:
        datetime: Wall time in UTC with ``tzinfo`` cleared for DB columns that
            store naive timestamps.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


MM_PER_INCH: float = 25.4


def _format_dimension_quantity(value: float) -> str:
    """Two decimal places, or a plain integer if *value* rounds to a whole number."""
    rounded = round(value + 0.0, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}"


def format_pin_dimension_mm(mm: float, unit: str) -> str:
    """Format a pin edge length stored in millimeters for display."""
    if unit == "in":
        return f"{_format_dimension_quantity(mm / MM_PER_INCH)} in"
    return f"{_format_dimension_quantity(mm)}mm"


def domain_from_url(url: str) -> str:
    """Return the host / authority portion of *url*.

    Args:
        url (str): Absolute or relative URL string.

    Returns:
        str: ``netloc`` from parsing (may be empty).
    """
    parse: ParseResult = urlparse(url)
    return parse.netloc


CURRENCY_DEFAULT_LOCALE: dict[str, str] = {
    # Americas
    "USD": "en_US",
    "CAD": "en_CA",
    "MXN": "es_MX",
    "BRL": "pt_BR",
    "ARS": "es_AR",
    "CLP": "es_CL",
    "COP": "es_CO",
    "PEN": "es_PE",
    "UYU": "es_UY",
    # Europe
    "EUR": "de_DE",  # neutral choice for Euro formatting
    "GBP": "en_GB",
    "CHF": "de_CH",
    "SEK": "sv_SE",
    "NOK": "nb_NO",
    "DKK": "da_DK",
    "PLN": "pl_PL",
    "CZK": "cs_CZ",
    "HUF": "hu_HU",
    "RON": "ro_RO",
    # Middle East + Africa
    "TRY": "tr_TR",
    "AED": "ar_AE",
    "SAR": "ar_SA",
    "ZAR": "en_ZA",
    "EGP": "ar_EG",
    "ILS": "he_IL",
    # Asia-Pacific
    "JPY": "ja_JP",
    "CNY": "zh_CN",
    "HKD": "zh_HK",
    "TWD": "zh_TW",
    "KRW": "ko_KR",
    "INR": "en_IN",
    "PKR": "ur_PK",
    "THB": "th_TH",
    "IDR": "id_ID",
    "VND": "vi_VN",
    "AUD": "en_AU",
    "NZD": "en_NZ",
    "SGD": "en_SG",
    "MYR": "ms_MY",
    "PHP": "en_PH",
}


def format_currency_code(
    amount: float | None, code: str, locale: str | None = None
) -> str:
    """Format *amount* as a localized currency string for an ISO currency *code*.

    Args:
        amount (float | None): Numeric value, or ``None`` for unknown amounts.
        code (str): ISO 4217 code such as ``"USD"`` or ``"EUR"``. ``"UNK"``
            yields the literal ``"Unknown"``.
        locale (str | None): Babel locale string; when ``None``, a default is
            picked from ``CURRENCY_DEFAULT_LOCALE`` or ``"en_US"``.

    Returns:
        str: Localized currency text, ``"Unknown"`` for missing amounts or
            ``UNK``, or a ``"{CODE} {amount}"`` fallback when Babel raises.
    """
    if amount is None:
        return "Unknown"
    code: str = code.upper().strip()
    if code == "UNK":
        return "Unknown"

    if locale is None:
        locale: str = CURRENCY_DEFAULT_LOCALE.get(code, "en_US")

    try:
        return format_currency(
            number=amount,
            currency=code,
            locale=locale,
        )
    except Exception:
        return f"{code} {amount:,.2f}"
