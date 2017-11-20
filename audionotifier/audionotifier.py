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
        self.audiocog = bot.get_cog('Audio')
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
            if self.bot.get_cog('AudioNotifier') is None:
                break
            for channel in self.active_chans:
                current = \
                    self.audiocog._get_queue_nowplaying(channel.server).title
                if current == self.last_updates[channel.server.id]:
                    continue
                else:
                    await self.notify(channel)
                    self.last_updates[channel.server.id] = current
            await asyncio.sleep(10)

    async def notify(self, channel: discord.Channel):
        srv = channel.server
        try:
            title = self.audiocog._get_queue_nowplaying(
                channel.server).title
            url = self.audiocog._get_queue_nowplaying(
                channel.server).webpage_url
        except AttributeError:
            return
        self.last_updates[channel.server.id] = title
        em = discord.Embed(title="Now Playing",
                           description='[{}]({})'.format(title, url),
                           color=srv.me.color)
        await self.bot.send_message(channel, embed=em)

    @checks.mod_or_permissions(manage_server=True)
    @commands.command(name="audionotify", no_pm=True, pass_context=True)
    async def audionotify(self, ctx):
        """
        set an audio notification channel
        """

        self.audiocog = self.bot.get_cog('Audio')
        if self.audiocog is None:
            return await self.bot.say('You need the audio cog loaded')

        await self.notify(ctx.message.channel)

        self.active_chans = [c for c in self.active_chans
                             if c.server != ctx.message.server]
        self.active_chans.append(ctx.message.channel)
        self.settings = [c.id for c in self.active_chans]
        self.save_settings()


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = AudioNotifier(bot)
    bot.add_cog(n)
