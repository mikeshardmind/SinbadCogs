import discord
import pathlib
from cogs.utils.dataIO import dataIO
from discord.ext import commands
from cogs.utils import checks
import asyncio
from __main__ import settings
assert discord

path = 'data/channelredirect'


class ChannelRedirect:
    """
    Block commands in specific channels
    and redirect the user to another channel
    """
    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}
        self.bot = bot

    def save_settings(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(name='blockcommandshere', no_pm=True, pass_context=True)
    async def nocommandshere(self, ctx, redirect: discord.Channel):
        """
        blocks commands in the channel called in, prompting users
        where they should use the commands
        """

        self.settings[ctx.message.channel.id] = redirect.id
        self.save_settings()
        await self.bot.say('Channel blocked.')

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(
        name='unblockcommandshere', no_pm=True, pass_context=True)
    async def reallowcommandshere(self, ctx):
        """
        unblocks commands in the channel called in
        """
        if self.settings.pop(ctx.message.channel.id, False) is False:
            return await self.bot.say('That channel was not blocked')
        self.save_settings()
        await self.bot.say('Channel unblocked.')

    async def notify(self, ctx):
        x = await self.bot.send_message(
            ctx.message.channel,
            'Hey! {0.mention} Use commands in <#{1}>'.format(
                ctx.message.author, self.settings[ctx.message.channel.id]))
        await asyncio.sleep(30)
        await self.bot.delete_message(x)
        if ctx.message.channel.permissions_for(
                ctx.message.server.me).manage_messages:
            await self.bot.delete_message(ctx.message)

    def __check(self, ctx):
        allowed = False
        allowed |= ctx.message.author.id == settings.owner \
            or ctx.message.author.id in ctx.bot.settings.co_owners
        allowed |= ctx.message.channel.id not in self.settings
        if not allowed:
            self.bot.loop.create_task(self.notify(ctx))
        return allowed


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = ChannelRedirect(bot)
    bot.add_cog(n)
