import discord
from discord.ext import commands
from cogs.utils import checks
from copy import deepcopy


class ChangeCTX:

    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.command(pass_context=True, name=changectx, aliases=['cctx'])
    async def changectx(self, ctx, chan: discord.Channel, *, command):
        """Run a command with a different context"""
        new_msg = deepcopy(ctx.message)
        new_msg.channel = chan
        new_msg.content = self.bot.settings.get_prefixes(new_msg.server)[0] \
            + command
        await self.bot.process_commands(new_msg)


def setup(bot):
    n = ChangeCTX(bot)
    bot.add_cog(n)
