from typing import Tuple, Union, NamedTuple

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
    obj: Union[commands.Command, commands.Cog]

    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str):
        ret = ctx.bot.get_command(arg)
        if ret:
            return cls("command", ret.qualified_name)
        ret = ctx.bot.get_cog(arg)
        if ret:
            return cls("cog", ret.__class__.__name__)
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
