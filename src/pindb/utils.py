from urllib.parse import urlparse

from babel.numbers import format_currency


def domain_from_url(url: str) -> str:
    parse = urlparse(url)
    return parse.netloc


CURRENCY_DEFAULT_LOCALE = {
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


def format_currency_code(amount: float, code: str, locale: str | None = None) -> str:
    """
    Format a number as a currency value based on ISO currency code.

    - `amount`:    Number to format.
    - `code`:      ISO currency code like "USD", "EUR", "JPY".
    - `locale`:    Override locale (optional). If None, a default is chosen automatically.
    """
    code = code.upper().strip()

    if locale is None:
        locale = CURRENCY_DEFAULT_LOCALE.get(code, "en_US")

    try:
        return format_currency(amount, code, locale=locale)
    except Exception:
        return f"{code} {amount:,.2f}"
