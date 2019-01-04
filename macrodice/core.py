from typing import Union, no_type_check
from random import randint

import dice

from redbot.core import commands
from redbot.core.config import Config


DIE_EMOJI = "\N{GAME DIE}"

_old_roll = None


class MacroDice(commands.Cog):
    """
    Dice Macros
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_member(
            macros={},
            dex=10,
            intel=10,
            con=10,
            wis=10,
            cha=10,
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

    def __unload(self):
        global _old_roll
        if _old_roll:
            self.bot.remove_command("roll")
            self.bot.add_command(_old_roll)

    @commands.guild_only()
    @commands.command(name="roll")
    @no_type_check
    async def roll(self, ctx: commands.Context, *, expr: Union[int, str]):
        """
        Roll something
        """

        try:
            if 100000 > expr > 0:
                await ctx.send(
                    f"{ctx.author.mention} {DIE_EMOJI} {randint(1, expr)} {DIE_EMOJI}"
                )
            else:
                await ctx.send("Use a number between 1-100000")
        except TypeError:
            try:
                result = dice.roll(expr)
            except Exception:
                await ctx.send("Invalid expression")
            else:
                await ctx.send(f"{ctx.author.mention} {result}")


def setup(bot):
    n = MacroDice(bot)
    global _old_roll
    _old_roll = bot.get_command("roll")
    if _old_roll:
        bot.remove_command(_old_roll.name)
    bot.add_cog(n)
