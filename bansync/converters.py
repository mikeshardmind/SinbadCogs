import shlex
import argparse
import re

from redbot.core.commands import Converter, Context, BadArgument, MemberConverter


class MemberOrID(MemberConverter):
    async def convert(self, ctx: Context, argument: str) -> int:

        try:
            m = await super().convert(ctx, arg)
        except Exception:
            pass
        else:
            return m.id

        match = self._get_id_match(argument) or re.match(r"<@!?([0-9]+)>$", argument)
        if match:
            return int(match.group(1))

        raise BadArgument()


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class SyndicatedConverter(Converter):
    """
    Handler for this
    """

    async def convert(self, ctx: Context, argument: str) -> dict:

        parser = NoExitParser(description="Syndicated Ban Syntax", add_help=False)
        parser.add_argument("--sources", nargs="*", dest="sources", default=[])
        parser.add_argument("--destinations", nargs="*", dest="dests", default=[])
        parser.add_argument(
            "--auto-destinations", action="store_true", default=False, dest="auto"
        )

        vals = parser.parse_args(shlex.split(argument))
        ret = {}

        guilds = set(ctx.bot.guilds)

        ret["sources"] = set(filter(lambda g: str(g.id) in vals.sources, guilds))
        if not ret["sources"]:
            raise BadArgument("I need at least 1 source.")

        if vals.auto:
            ret["dests"] = guilds - ret["sources"]
            ret["auto"] = True
        elif vals.dests:
            ret["dests"] = set()
            for guild in guilds:
                to_comp = str(guild.id)
                if to_comp in vals.dests and to_comp not in ret["sources"]:
                    ret["dests"].add(guild)
        else:
            raise BadArgument(
                "I need either at least one destination, or to be told to try everywhere not a source."
            )
        ret["usr"] = ctx.author
        return ret
