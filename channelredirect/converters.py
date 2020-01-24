from __future__ import annotations

from typing import Union, NamedTuple

from redbot.core import commands


class CommandConverter(NamedTuple):
    com: commands.Command

    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str):
        ret = ctx.bot.get_command(arg)
        if ret:
            return cls(ret)
        raise commands.BadArgument('Command "{arg}" not found.'.format(arg=arg))


class CogOrCOmmand(NamedTuple):
    stype: str
    obj: str

    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str):
        if (com := ctx.bot.get_command(arg)) :
            return cls("command", com.qualified_name)
        if (cog := ctx.bot.get_cog(arg)) :
            return cls("cog", cog.__class__.__name__)
        raise commands.BadArgument('Cog or Command "{arg}" not found.'.format(arg=arg))


class TrinaryBool(NamedTuple):
    state: Union[bool, None]

    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str):
        try:
            ret = {"allow": True, "deny": False, "clear": None}[arg.lower()]
        except KeyError:
            raise commands.BadArgument(
                "Was expecting one of `allow`, `deny`, or `clear`, got {arg}".format(
                    arg=arg
                )
            )
        else:
            return cls(ret)
