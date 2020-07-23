from __future__ import annotations

from typing import Optional

import discord
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


_role_converter = commands.RoleConverter()


class NonEveryoneRole(discord.Role):
    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str) -> discord.Role:
        role: discord.Role = await _role_converter.convert(ctx, arg)
        if role.is_default():
            raise commands.BadArgument("You can't set this for the everyone role")
        return role
