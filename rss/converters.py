from __future__ import annotations

from typing import Optional

from redbot.core import commands


def _tristate(arg: str) -> Optional[bool]:
    if arg.lower() in ("true", "yes"):
        return True
    if arg.lower() in ("false", "no"):
        return False
    if arg.lower() in ("none", "default"):
        return None
    raise commands.BadArgument(
        f'"{arg}" is not a valid setting.'
        ' Valid settings are "true" or "false", or "default" to '
        "remove the setting"
    )


class TriState:
    def __init__(self, state):
        self.state = state

    @classmethod
    async def convert(cls, ctx, arg):
        return cls(_tristate(arg))
