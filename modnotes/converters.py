import contextlib
import re
from typing import NamedTuple, Optional

import discord
from redbot.core.commands import Context, BadArgument, MemberConverter

_discord_member_converter_instance = MemberConverter()
_id_regex = re.compile(r"([0-9]{15,21})$")
_mention_regex = re.compile(r"<@!?([0-9]{15,21})>$")


class MemberOrID(NamedTuple):
    member: Optional[discord.Member]
    id: int

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        with contextlib.suppress(Exception):
            m = await _discord_member_converter_instance.convert(ctx, argument)
            return cls(m, m.id)

        match = _id_regex.match(argument) or _mention_regex.match(argument)
        if match:
            return cls(None, int(match.group(1)))

        raise BadArgument()
