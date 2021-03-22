#   Copyright 2017-present Michael Hall
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import contextlib
import re
from typing import NamedTuple, Optional

import discord
from redbot.core.commands import BadArgument, Context, MemberConverter

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
