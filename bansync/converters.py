import shlex
import argparse

from redbot.core.commands import Converter, Context, BadArgument


class SyndicatedConverter(Converter):
    """
    Handler for this
    """

    async def convert(self, ctx: Context, argument: str) -> dict:

        parser = argparse.ArgumentParser(
            description="Syndicated Ban Syntax", add_help=False, allow_abbrev=True
        )
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
        elif vals.dests:
            ret["dests"] = set()
            for guild in guilds:
                to_comp = str(guild.id)  # PEP 505 when?
                if to_comp in vals.dests and to_comp not in ret["sources"]:
                    ret["dests"].add(guild)
        else:
            raise BadArgument(
                "I need either at least one destination, or to be told to try everywhere not a source."
            )
        ret["usr"] = ctx.author
        return ret
