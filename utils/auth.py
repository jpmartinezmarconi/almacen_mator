import os
from typing import Optional


def get_password(name: str) -> Optional[str]:
    return os.environ.get(name) or None
