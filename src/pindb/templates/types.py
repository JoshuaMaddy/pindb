"""
htpy page and fragment builders: `templates/types.py`.
"""

from typing import Sequence

from htpy import BaseElement, Fragment

SingleContent = BaseElement | Fragment | str | None
BooledContent = Sequence[bool | SingleContent]
Content = SingleContent | BooledContent
