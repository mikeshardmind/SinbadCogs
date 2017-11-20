import pathlib
import asyncio
import discord
from discord.ext import commands
from .utils import checks
from cogs.utils.dataIO import dataIO

path = 'data/audionotifier'


class AudioNotifier:
    """
    Audio notification cog
    """

    __version__ = "1.1.0"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        self.bot = bot
        self.last_updates = {}
        self.active_chans = []
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = []
        self.active_chans = [c for c in bot.get_all_channels()
                             if c.id in self.settings]
        self.bot.loop.create_task(self.task_notifier())

    def save_settings(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    async def task_notifier(self):
        while True:
            for channel in self.active_chans:
                srv = channel.server
                current = self.bot.get_cog('Audio')._get_queue_nowplaying(
                    srv).title
                if current == self.last_updates.pop(srv.id, None):
                    pass
                else:
                    try:
                        title = self.bot.get_cog(
                            'Audio')._get_queue_nowplaying(
                                srv).title
                        url = self.bot.get_cog(
                            'Audio')._get_queue_nowplaying(
                                srv).webpage_url
                    except AttributeError:
                        pass
                    else:
                        em = discord.Embed(title="Now Playing",
                                           description='[{}]({})'.format(
                                                title, url),
                                           color=srv.me.color)
                        await self.bot.send_message(channel, embed=em)
                        self.last_updates[channel.server.id] = current

            await asyncio.sleep(2)

    async def notify(self, channel: discord.Channel):
        srv = channel.server
        try:
            title = self.bot.get_cog('Audio')._get_queue_nowplaying(
                channel.server).title
            url = self.bot.get_cog('Audio')._get_queue_nowplaying(
                channel.server).webpage_url
        except AttributeError:
            raise
            return
        em = discord.Embed(title="Now Playing",
                           description='[{}]({})'.format(title, url),
                           color=srv.me.color)
        await self.bot.send_message(channel, embed=em)

    @checks.mod_or_permissions(manage_server=True)
    @commands.command(name="audionotifierset", no_pm=True, pass_context=True)
    async def audionotiferset(self, ctx):
        """
        set an audio notification channel
        """

        if self.bot.get_cog('Audio') is None:
            return await self.bot.say('You need the audio cog loaded')

        self.active_chans = [c for c in self.active_chans
                             if c.server != ctx.message.server]
        self.active_chans.append(ctx.message.channel)
        self.settings = [c.id for c in self.active_chans]
        self.save_settings()

    @commands.command(name="whatsplaying", no_pm=True, pass_context=True)
    async def whatisthis(self, ctx):
        """
        find out what the bot is playing
        """

        if self.bot.get_cog('Audio') is None:
            return await self.bot.say('Nothing')
        try:
            await self.notify(ctx.message.channel)
        except AttributeError:
            return await self.bot.say('Nothing')


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = AudioNotifier(bot)
    bot.add_cog(n)
