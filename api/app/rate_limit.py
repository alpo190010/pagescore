"""Rate limiter singleton — shared between main.py and router modules.

headers_enabled is False because slowapi's header injection requires a
Response parameter in sync endpoint signatures, which clashes with FastAPI's
dict-return convention.  Retry-After is still sent on 429 responses via the
_rate_limit_exceeded_handler.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, headers_enabled=False)
