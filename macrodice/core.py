from random import randint
from typing import Union, no_type_check

import dice
from redbot.core import commands
from redbot.core.config import Config
from cog_shared.sinbad_libs import extra_setup


DIE_EMOJI = "\N{GAME DIE}"

_old_roll = None


class MacroDice(commands.Cog):
    """
    Dice Macros
    """

    __version__ = "1.0.2"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_member(
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

    def cog_unload(self):
        global _old_roll
        if _old_roll:
            try:
                self.bot.remove_command("roll")
            except AttributeError:  # fucking requires + module cleanup ordering....
                pass  # This isn't a supress. I need to be reminded to PR a fix (TODO)
            self.bot.add_command(_old_roll)

    @commands.guild_only()
    @commands.command(name="roll")
    @no_type_check
    async def roll(self, ctx: commands.Context, *, expr: Union[int, str]):
        """
        Roll something
        """

        await self.handle_expression(ctx, expr)

    @staticmethod
    async def handle_expression(ctx, expr):

        try:
            if 100000 > expr > 0:
                await ctx.send(
                    f"{ctx.author.mention} {DIE_EMOJI} {randint(1, expr)} {DIE_EMOJI}"
                )
            else:
                await ctx.send("Use a number between 1-100000")
        except TypeError:

            def handler(exp):
                real = dice.roll(exp)
                mx = dice.roll_max(exp)
                mn = dice.roll_min(exp)
                try:
                    yield from zip(real, mn, mx)
                except TypeError:
                    yield (real, mn, mx)

            def get_formatted(an_expr):
                return "\n".join(
                    f"{actual:<4} (Range: {low}-{high})"
                    for actual, low, high in handler(an_expr)
                )

            # noinspection PyBroadException
            try:
                result = get_formatted(expr)
            except Exception:
                await ctx.send("Invalid expression")
            else:
                await ctx.send(f"{ctx.author.mention}\n```\n{result}\n```")

    @commands.guild_only()
    @commands.command(name="makemacro")
    async def mmac(self, ctx, name, *, expression):
        """
        hmmm
        """
        grp = self.config.member(ctx.author)

        async with grp.macros() as data:
            data.update({name: expression})
        await ctx.tick()

    @commands.guild_only()
    @commands.command(name="removemacro")
    async def rmmac(self, ctx, name):
        """
        hmm?
        """
        grp = self.config.member(ctx.author)

        async with grp.macros() as data:
            data.pop(name, None)
        await ctx.tick()

    @commands.guild_only()
    @commands.command(name="mroll")
    async def mroll(self, ctx, name):
        """
        Rolls a macro
        """

        data = await self.config.member(ctx.author).all()

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
    async def statset(self, ctx, name, value: int):
        """
        ...
        """

        grp = self.config.member(ctx.author)

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


@extra_setup
def setup(bot):
    n = MacroDice(bot)
    global _old_roll
    _old_roll = bot.get_command("roll")
    if _old_roll:
        bot.remove_command(_old_roll.name)
    bot.add_cog(n)
