"""Process-lifetime token for ``?v=`` on first-party ``/templates-js`` script URLs.

Paired with long ``immutable`` cache headers: restart/deploy bumps the query so
browsers fetch new bytes.
"""

import time

STATIC_CACHE_BUSTER: str = str(int(time.time()))
