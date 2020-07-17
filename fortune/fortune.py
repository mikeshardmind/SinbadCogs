import json
import random
from typing import List, Optional

from redbot.core import commands
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import box

from .cows import cowsay


class Moo:
    @classmethod
    async def convert(cls, ctx, arg):
        if arg[:3].lower() == "moo":
            return cls()

        raise commands.BadArgument()


class Fortune(commands.Cog):
    """
    A Cog for displaying Unix-like Fortunes
    """

    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )

    def __init__(self, bot):
        self.bot = bot
        self._data: List[str]
        path = bundled_data_path(self) / "fortunes.json"
        with path.open(mode="r", encoding="utf-8") as fp:
            self._data = json.load(fp)

    @commands.cooldown(1, 30)
    @commands.command(usage="")
    async def fortune(
        self, ctx: commands.Context, what_does_the_cowsay: Optional[Moo] = None
    ):
        """
        Get a random fortune message.
        """
        fortune = random.choice(self._data)  # nosec
        if what_does_the_cowsay:
            await ctx.invoke(self._cowsay, what_does_the_cowsay=fortune)
            return
        await ctx.send(box(fortune))

    @commands.cooldown(1, 30)
    @commands.command(hidden=True, name="cowsay")
    async def _cowsay(self, ctx: commands.Context, *, what_does_the_cowsay: str = ""):
        """
        Moo.
        """
        if not what_does_the_cowsay:
            await ctx.send_help()
            return

        if len(what_does_the_cowsay) > 1500:
            await ctx.send("Moo.")
            return

        await ctx.send(box(cowsay(what_does_the_cowsay)))
