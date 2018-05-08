import dice as dicelib
from discord.ext import commands
from redbot.core import RedContext, checks
from redbot.core.bot import Red
import random
from .dice import StatefulDie

com_objs = {}
general_coms = ['flip', 'rps', '8', 'stopwatch', 'lmgtfy', 'hug',
                'userinfo', 'serverinfo', 'urban', 'ping', 'roll', 'choose']
keep_coms = ['userinfo', 'ping', 'hug']


class GenReplace:
    """
    Replacing the general cog a bit at a time
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self._dice = {}

    def __unload(self):
        for com in com_objs.values():
            self.bot.add_command(com)

    @checks.admin()
    @commands.guild_only()
    @commands.command(hidden=True)
    async def enablestateful(self, ctx: RedContext, enable: bool=True):
        """
        enables dice less prone to streaks
        """
        self._dice[ctx.guild.id] = self._dice.get(ctx.guild.id, {})

    @commands.command()
    async def dice(self, ctx, expr: str):
        """
        Rolls a dice expression

        Modifiers include basic algebra, 't' to total a result,
        's' to sort multiple rolls, '^n' to only use the n highest rolls, and
        'vn' to use the lowest n rolls. This cog uses the dice library.
        The full list of operators can be found at:
        https: // github.com/borntyping/python-dice  # notation
        Examples: 4d20, d100, 6d6v2, 8d4t, 4d4 + 4, 6d8 ^ 2
        """
        # This is less featured than
        # https://github.com/calebj/calebj-cogs/blob/master/dice/dice.py
        # Go use it instead if you don't want this.

        result = dicelib.roll(expr)
        response = ctx.author.mention + ": " + str(result)
        if len(response) > 1000:  # No spam K
            return
        await ctx.maybe_send_embed(response)

    @commands.command()
    async def roll(self, ctx: RedContext, sides: int=6):
        """
        Rolls a die
        """
        if sides < 1:
            return
        if ctx.guild is None \
            or ctx.guild.id not in self._dice \
                or sides not in (4, 6, 8, 10, 12, 20):
            roll = random.randrange(1, sides)
        else:
            dice = self._dice
            die = dice[ctx.guild.id].get(ctx.author.id, {}).get(sides, None)
            if die is None:
                dice[ctx.guild.id][ctx.author.id][sides] = StatefulDie(sides)
            roll = dice[ctx.guild.id][ctx.author.id][sides].roll()

        return await ctx.maybe_send_embed("{} :{}".format(
            ctx.author, roll)
        )


def setup(bot):
    com_objs = {
        k: bot.get_command(k) for k in general_coms
        if k not in keep_coms
    }
    for k, v in com_objs.items():
        if v is not None:
            bot.remove_command(k)
    # TODO: Make ^ configable
    bot.add_cog(GenReplace(bot))
