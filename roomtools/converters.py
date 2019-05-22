import re
from typing import NamedTuple, Optional
from redbot.core.commands import Context, BadArgument


pattern = re.compile(r"\b--user-limit\b|\b-u\b")


class TempChannelConverter(NamedTuple):
    name: str
    user_limit: Optional[int] = None

    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        arg = argument.strip()
        try:
            nm, ul = pattern.split(argument, maxsplit=1)
        except ValueError:
            return cls(arg)

        try:
            user_limit = int(ul.strip())
        except ValueError:
            raise BadArgument()

        return cls(nm.strip(), user_limit)
