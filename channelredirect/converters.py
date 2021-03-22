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

from typing import NamedTuple, Union

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
        # mypy doesn't do type narrowing for the walrus yet
        if com := ctx.bot.get_command(arg):
            assert com, "mypy"  # nosec
            return cls("command", com.qualified_name)
        if cog := ctx.bot.get_cog(arg):
            assert cog, "mypy"  # nosec
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
