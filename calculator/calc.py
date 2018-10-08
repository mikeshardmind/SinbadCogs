import sys
import subprocess
from typing import Any

from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n

from .jailer import run_jailed

_ = Translator("Calculator", __file__)


@cog_i18n(_)
class Calculator(commands.Cog):
    """
    This provides a safe(er) method for allowing math
    to be evaluated by the bot.

    This utilizes asteval paired with resource limited subproccesses

    This should be safe for use on linux.
    I am preventing use of it on other platforms
    due to lack of testing and confidence it would be safe there.

    This cog can only run if the bot can use resource.setrlimit.
    This usually means a bot running as root.
    I won't support making that happen.
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0.2b"

    def __init__(self, bot):
        self.bot = bot

    def __local_check(self, ctx):
        return sys.platform == "linux"

    @commands.command(name="calc", aliases=["calculate"])
    async def calculate(self, ctx: commands.Context, *, expression: str = ""):
        """
        get the result of an expression

        a few predefined values exist for your convienience:

        e: e
        pi: pi
        gamma: Eueler's constant

        libs imported and available for use:
        numpy
        math
        """

        if not expression:
            return await ctx.send_help()
        try:
            await run_jailed(ctx=ctx, expr=expression)
        except subprocess.SubprocessError:
            await ctx.maybe_send_embed(
                "Your bot cannot make a required system call `resource.setrlimit`"
            )
            ctx.bot.remove_command(ctx.command.name)
