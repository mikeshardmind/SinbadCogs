import argparse
import contextlib
import re
import shlex
from dataclasses import dataclass
from typing import NamedTuple, Optional, Set

import discord
from redbot.core.commands import Context, BadArgument, MemberConverter
from redbot.core.i18n import Translator

_ = Translator("BanSync", __file__)


class ParserError(Exception):
    pass


_discord_member_converter_instance = MemberConverter()
_id_regex = re.compile(r"([0-9]{15,21})$")
_mention_regex = re.compile(r"<@!?([0-9]{15,21})>$")


class MemberOrID(NamedTuple):
    member: Optional[discord.Member]
    id: Optional[int]

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        with contextlib.suppress(Exception):
            m = await _discord_member_converter_instance.convert(ctx, argument)
            return cls(m, m.id)

        match = _id_regex.match(argument) or _mention_regex.match(argument)
        if match:
            return cls(None, int(match.group(1)))

        raise BadArgument()


class NoExitParser(argparse.ArgumentParser):
    """By default, an error on this calls sys.exit"""

    def error(self, message):
        # Specifically not a parser error, which we have custom handling for.
        raise BadArgument() from None


@dataclass
class SyndicatedConverter:
    """
    Parser based converter.

    Takes sources, and either
        destinations, a flag to automatically determine destinations, or both
    """

    sources: Set[discord.Guild]
    dests: Set[discord.Guild]
    usr: discord.User
    shred_ratelimits: bool = False
    auto: bool = False

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        parser = NoExitParser(description="Syndicated Ban Syntax", add_help=False)
        parser.add_argument("--sources", nargs="*", dest="sources", default=[])
        parser.add_argument("--destinations", nargs="*", dest="dests", default=[])
        parser.add_argument(
            "--auto-destinations", action="store_true", default=False, dest="auto"
        )
        parser.add_argument(
            "--shred-ratelimits",
            action="store_true",
            default=False,
            dest="shred_ratelimits",
        )

        vals = parser.parse_args(shlex.split(argument))

        guilds = set(ctx.bot.guilds)

        sources = set(filter(lambda g: str(g.id) in vals.sources, guilds))
        if not sources:
            raise ParserError(_("I need at least 1 source.")) from None

        if vals.auto:
            destinations = guilds - sources
        elif vals.dests:
            destinations = set()
            for guild in guilds:
                to_comp = str(guild.id)
                if to_comp in vals.dests and to_comp not in sources:
                    destinations.add(guild)
        else:
            raise ParserError(
                _(
                    "I need either at least one destination, "
                    " to be told to automatically determine destinations, "
                    "or a combination of both to add extra destinations beyond the automatic."
                )
            ) from None

        return cls(
            sources=sources,
            dests=destinations,
            shred_ratelimits=vals.shred_ratelimits,
            auto=vals.auto,
            usr=ctx.author,
        )
