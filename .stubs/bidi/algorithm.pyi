# Incomplete, good enough stub.
from typing import Optional

def get_display(
    unicode_or_str: str,
    *,
    encoding: str = "utf-8",
    upper_is_rtl: bool = False,
    base_dir: Optional[bool] = None,
    debug: bool = False,
) -> str: ...
