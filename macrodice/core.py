from typing import Union, no_type_check
from random import randint

import dice
import discord

from redbot.core import commands, checks
from redbot.core.config import Config

DIE_EMOJI = "\N{GAME DIE}"


class MacroDice(commands.Cog):
    """
    Dice Macros
    """

    def __init__(self, bot, old_roll=None):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_member(macros={})
        self._old_roll = old_roll

    def __unload(self):
        self.bot.add_command(self._old_roll)

    @commands.guild_only()
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
            except dice.DiceException:
                await ctx.send("Invalid expression")
            else:
                await ctx.send(result)
