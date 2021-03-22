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

from __future__ import annotations

from typing import NamedTuple, Optional

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


class FieldAndTerm(NamedTuple):
    field: str
    term: str

    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str) -> FieldAndTerm:

        try:
            field, term = arg.casefold().split(maxsplit=1)
        except ValueError:
            raise commands.BadArgument("Must provide a field and a term to match")

        return cls(field, term)
