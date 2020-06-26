from typing import TYPE_CHECKING

from redbot.core import commands

if TYPE_CHECKING:
    from . import RoomTools


def tmpc_active():
    async def check(ctx: commands.Context):
        if not ctx.guild:
            return False
        cog = ctx.bot.get_cog("RoomTools")
        if TYPE_CHECKING:
            assert isinstance(cog, RoomTools)  # nosec
        if not cog:
            return False
        return await cog.tmpc_config.guild(ctx.guild).active()

    return commands.check(check)


def aa_active():
    async def check(ctx: commands.Context):
        if not ctx.guild:
            return False
        cog = ctx.bot.get_cog("RoomTools")
        if TYPE_CHECKING:
            assert isinstance(cog, RoomTools)  # nosec
        if not cog:
            return False
        return await cog.ar_config.guild(ctx.guild).active()

    return commands.check(check)
