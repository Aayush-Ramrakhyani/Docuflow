"""
Shared slowapi Limiter instance.
Defined here (not in main.py) so endpoints can import it without circular deps.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
