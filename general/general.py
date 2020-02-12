from __future__ import annotations

from random import randint
from typing import Union, Iterable, SupportsInt

import dice
from redbot.cogs.general.general import General as RedGeneral
from redbot.core import commands
from redbot.core.config import Config


def as_iterable(item: Union[Iterable, SupportsInt]) -> Iterable:
    if isinstance(item, Iterable):
        return item
    else:
        return (item,)


class General(RedGeneral):
    """
    Mostly just for the dice.
    """

    __version__ = "330.0.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return (
            f"{pre_processed}"
            f"\nThis is a replacement providing a different roll command"
            f"\nCog Version: {self.__version__}"
        )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.roll_config = Config.get_conf(
            None,
            identifier=78631113035100160,
            force_registration=True,
            cog_name="MacroDice",
        )
        self.roll_config.register_member(
            macros={},
            dexterity=10,
            intelligence=10,
            constitution=10,
            wisdom=10,
            charisma=10,
            strength=10,
            level=1,
        )

    # Yes, these are the correct 5th edition formulas.

    @staticmethod
    def proficiency(level: int) -> int:
        return (level + 7) // 4

    @staticmethod
    def modifier(stat: int) -> int:
        return (stat - 10) // 2

    @commands.guild_only()
    @commands.command(name="roll")
    async def roll(self, ctx: commands.Context, *, expr: Union[int, str]):
        """
        Roll something
        """

        await self.handle_expression(ctx, expr)

    @staticmethod
    async def handle_expression(ctx: commands.Context, expr: Union[int, str]):

        if isinstance(expr, int):
            if 100000 > expr > 0:
                DIE = "\N{GAME DIE}"
                randnum = randint(1, expr)  # nosec
                await ctx.send(f"{ctx.author.mention} {DIE} {randnum} {DIE}")
            else:
                await ctx.send("Use a number between 1-100000")
        else:

            def handler(exp):
                real = as_iterable(dice.roll(exp))
                mn = as_iterable(dice.roll_min(exp))
                mx = as_iterable(dice.roll_max(exp))
                yield from zip(real, mn, mx)

            def get_formatted(an_expr):
                return "\n".join(
                    f"{actual:<4} (Range: {low}-{high})"
                    for actual, low, high in handler(an_expr)
                )

            try:
                result = get_formatted(expr)
            except Exception:
                await ctx.send("Invalid expression")
            else:
                m = f"{ctx.author.mention}\n```\n{result}\n```"
                if len(m) > 1800:
                    m = "Oops, too many dice, I dropped some"
                await ctx.send(m)

    @commands.guild_only()
    @commands.command(name="makemacro")
    async def mmac(self, ctx: commands.Context, name: str, *, expression: str):
        """
        hmmm
        """
        grp = self.roll_config.member(ctx.author)

        async with grp.macros() as data:
            data.update({name: expression})
        await ctx.tick()

    @commands.guild_only()
    @commands.command(name="removemacro")
    async def rmmac(self, ctx: commands.Context, name: str):
        """
        hmm?
        """
        grp = self.roll_config.member(ctx.author)

        async with grp.macros() as data:
            data.pop(name, None)
        await ctx.tick()

    @commands.guild_only()
    @commands.command(name="mroll")
    async def mroll(self, ctx: commands.Context, name: str):
        """
        Rolls a macro
        """

        data = await self.roll_config.member(ctx.author).all()

        try:
            macro = data["macros"][name]
        except KeyError:
            return await ctx.send("No such macro")

        data.pop("macros", None)

        lv = data.pop("level")

        mods = {f"{k[:3]} mod": self.modifier(v) for k, v in data.items()}
        data["pbonus"] = self.proficiency(lv)
        data["level"] = lv
        data.update(mods)
        expression = macro.format(**data)

        await self.handle_expression(ctx, expression)

    @commands.guild_only()
    @commands.command(name="statset")
    async def statset(self, ctx: commands.Context, name: str, value: int):
        """
        ...
        """

        grp = self.roll_config.member(ctx.author)

        name = name.lower()

        async with grp() as data:  # type: dict
            vkeys = {k[:3]: k for k in data.keys() if k != "macros"}
            if name in vkeys:
                name = vkeys[name]

            if name not in vkeys.values():
                return await ctx.send(
                    f"Invalid name, valid names are: {', '.join(vkeys.values())}"
                )

            data.update({name: value})
        await ctx.tick()
