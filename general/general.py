from __future__ import annotations

from discord.ext import commands
from redbot.core import commands as red_commands
from redbot.core.utils.chat_formatting import box, pagify

from .dice import DiceError, Expression


class General(red_commands.Cog):
    """
    Just a better roll command, the rest can go.
    """

    __version__ = "330.1.0"
    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return (
            f"{pre_processed}"
            f"\nThis is a replacement providing a different roll command"
            f"\nCog Version: {self.__version__}"
        )

    @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    @commands.command(name="roll", cls=red_commands.Command)
    async def roll(self, ctx: commands.Context, *, expression: str):
        """ Roll some dice """

        if len(expression) > 500:
            return await ctx.send("I'm not even going to try and parse that one")

        try:
            ex = Expression.from_str(expression)
            v, msg = ex.verbose_roll()
        except ZeroDivisionError:
            return await ctx.send("Oops, too many dice. I dropped them")
        except DiceError as err:
            return await ctx.send(f"{ctx.author.mention}: {err}", delete_after=15)

        prepend = (
            f"{ctx.author.mention} Results for {ex} "
            f"\N{GAME DIE} Total: {v} "
            f"\nBreakdown below"
        )

        for page in pagify(
            msg, escape_mass_mentions=False, page_length=1800, shorten_by=0
        ):
            await ctx.send(f"{prepend}\n{box(page)}")

    @commands.cooldown(3, 30, commands.BucketType.member)
    @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    @commands.command(name="diceinfo", cls=red_commands.Command)
    async def rverb(self, ctx, *, expression: str):
        """
        Get info about an expression
        """

        try:
            ex = Expression.from_str(expression)
            low, high, ev = ex.get_min(), ex.get_max(), ex.get_ev()
        except ZeroDivisionError:
            return await ctx.send("Oops, too many dice. I dropped them")
        except DiceError as err:
            return await ctx.send(f"{ctx.author.mention}: {err}", delete_after=15)

        await ctx.send(
            f"Information about dice Expression: {ex}:\nLow: {low}\nHigh: {high}\nEV: {ev:.7g}"
        )
