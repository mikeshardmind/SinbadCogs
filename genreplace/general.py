import dice as dicelib
from discord.ext import commands
from redbot.core import RedContext, checks
from redbot.core.bot import Red

from .roll import roll as roll_com_obj

com_objs = {}
general_coms = ['flip', 'rps', '8', 'stopwatch', 'lmgtfy', 'hug',
                'userinfo', 'serverinfo', 'urban', 'ping', 'roll', 'choose']
keep_coms = ['userinfo', 'ping', 'hug']


class GeneralReplacements:
    """
    Replacing the general cog a bit at a time
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self._dice = {}
        r = commands.Command(callback=roll_com_obj, name='roll')
        r.instance = bot.get_cog('General')
        bot.add_command(r)

    def __unload(self):
        x = self.bot.get_cog('General')
        if x.stateful_dice:
            del x.stateful_dice
        for com in com_objs.values():
            try:
                self.bot.add_command(com)
            except Exception:
                pass

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


def setup(bot):
    com_objs = {
        k: bot.get_command(k) for k in general_coms
        if k not in keep_coms
    }
    for k, v in com_objs.items():
        if v is not None:
            bot.remove_command(k)
    # TODO: Make ^ configable
    bot.add_cog('GeneralReplacements')
