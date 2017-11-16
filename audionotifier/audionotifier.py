import discord
from discord.ext import commands
from .utils import checks
import asyncio


class AudioNotifier:
    """
    Audio notification cog
    """

    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        self.bot = bot
        self.audiocog = bot.get_cog('Audio')
        self.last_updates = {}
        self.active_chans = []
        self.bot.loop.create_task(self.task_notifier())

    async def task_notifier(self):
        for channel in self.active_server_chans:
            current = self.audiocog._get_queue_nowplaying(channel.server).title
            if current == self.last_updates[channel.server.id]:
                continue
            else:
                await self.notify(channel)
                self.last_updates[channel.server.id] = current
        await asyncio.sleep(10)

    async def notify(self, channel: discord.Channel):
        srv = channel.server
        try:
            title = self.audiocog._get_queue_nowplaying(channel.server).title
            url = self.audiocog._get_queue_nowplaying(channel.server).url
        except AttributeError:
            return
        em = discord.Embed(description="\u200b", color=srv.me.color)
        em.add_field(name='Now playing',
                     value='[{}]({})'.format(title, url),
                     inline=True)
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


def setup(bot):
    n = AudioNotifier(bot)
    bot.add_cog(n)
