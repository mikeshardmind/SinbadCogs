from redbot.core import RedContext
import random
from .dice import StatefulDie


async def roll(ctx: RedContext, sides: int=6):
    """
    Rolls a die
    """
    if sides < 1:
        return
    if ctx.guild is None \
        or ctx.guild.id not in ctx.bot.get_cog('GeneralReplacements')._dice \
            or sides not in (4, 6, 8, 10, 12, 20):
        roll = random.randrange(1, sides)
    else:
        dice = ctx.bot.get_cog('GeneralReplacements')._dice
        die = dice[ctx.guild.id].get(ctx.author.id, {}).get(sides, None)
        if die is None:
            dice[ctx.guild.id][ctx.author.id][sides] = StatefulDie(sides)
        roll = dice[ctx.guild.id][ctx.author.id][sides].roll()

    return await ctx.maybe_send_embed("{} :{}".format(
        ctx.author, roll)
    )
