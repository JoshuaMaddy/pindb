"""Process-lifetime token for optional ``?v=`` on first-party script URLs."""

import time

STATIC_CACHE_BUSTER: str = str(int(time.time()))
