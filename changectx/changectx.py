import discord
from discord.ext import commands
from .utils import checks
import time
from random import randint


class ChangeCTX:

    def __init__(self, bot):
        self.bot = bot
        self.context = None
        self.impersonate = None

    @checks.is_owner()
    @commands.command(name="setcontext", pass_context=True)
    async def set_context(self, ctx, channel_id: str):

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return await self.bot.say("Channel not found")
        if channel.type != discord.ChannelType.text:
            return await self.bot.say("Try again with a text channel")

        self.context = channel
        await self.bot.say("Context set to channel {0.name}".format(channel))

    @checks.is_owner()
    @commands.command(name="setauthor", pass_context=True)
    async def set_impersonate(self, ctx, user_id: str=None):

        self.impersonate = user_id
        await self.bot.say("Impersonate ID set")

    @checks.is_owner()
    @commands.command(name="runincontext", pass_context=True)
    async def run_in_context(self, ctx, *, com: str):

        if self.context is None and self.impersonate is None:
            return await \
                self.bot.say("Hint: `{0.prefix}setcontext`"
                             "and/or `{0.prefix}setauthor`".format(ctx))

        chan = ctx.message.channel if self.context is None \
            else self.context

        try:
            server = chan.server
            prefix = self.bot.settings.get_prefixes(server)[0]
        except AttributeError:
            return await self.bot.say("Are you sure I can see that channel?")

        author_id = ctx.message.author.id if self.impersonate is None \
            else self.impersonate

        data = \
            {'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime()),
             'content': prefix + com,
             'channel': chan,
             'channel_id': chan.id,
             'author': {'id': author_id},
             'nonce': randint(-2**32, (2**32) - 1),
             'id': randint(10**(17), (10**18) - 1),
             'reactions': []
             }
        message = discord.Message(**data)

        self.bot.dispatch('message', message)


def setup(bot):
    n = ChangeCTX(bot)
    bot.add_cog(n)
