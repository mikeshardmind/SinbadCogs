import discord
from discord.ext import commands
import pathlib
from cogs.utils.dataIO import dataIO
from .utils import checks


path = 'data/antispotify'


class AntiSpotify:
    """
    Because blocking links to block just spotify is dumb
    """

    __author__ = "mikeshardmind (Sinbad#0001)"
    __version__ = "1.0.0a"

    def __init__(self, bot):
        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}

    def save_json(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    def init_server(self, server: discord.Server, reset=False):
        if server.id not in self.settings or reset:
            self.settings[server.id] = {
                'active': False,
                'whitelist': []
            }

    @commands.group(name='antispotify', pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def _group(self, ctx):
        """
        settings for antispotify
        """

        if ctx.invoked_subcommand is None:
            await self.bot.send_help(ctx)

    @_group.command(name='toggle', pass_context=True, no_pm=True)
    async def toggler(self, ctx):
        """
        toggles it on/off
        """
        server = ctx.message.server

        self.init_server(server)
        self.settings[server.id]['active'] ^= True
        self.save_json()
        status = "on" if self.settings[server.id]['active'] else "off"
        await self.bot.say('Spotify filtering is {}.'.format(status))

    @_group.command(name='whitelist', pass_context=True, no_pm=True)
    async def whitelist(self, ctx, channel: discord.Channel):
        """
        add a channel where spotify is allowed (if you want)
        """

        server = ctx.message.server
        self.init_server(server)

        if channel.id in self.settings[server.id]['whitelist']:
            return await self.bot.say('Channel already whitelisted')
        self.settings[server.id]['active'].append(channel.id)
        self.save_json()
        await self.bot.say('Channel whitelisted.')

    @_group.command(name='unwhitelist', pass_context=True, no_pm=True)
    async def unwhitelist(self, ctx, channel: discord.Channel):
        """
        unwhitelist a channel
        """

        server = ctx.message.server
        self.init_server(server)

        if channel.id not in self.settings[server.id]['whitelist']:
            return await self.bot.say('Channel wasn\'t whitelisted')
        self.settings[server.id]['active'].remove(channel.id)
        self.save_json()
        await self.bot.say('Channel unwhitelisted.')

    @_group.command(name='reset', pass_context=True, no_pm=True)
    async def rset(self, ctx):
        """
        resets to defaults
        """

        server = ctx.message.server
        self.init_server(server, True)
        await self.bot.say('Settings reset')

    async def _spoti_check(self, message):
        mdata = await self.bot.http.get_message(message.channel.id, message.id)
        if mdata is not None:
            if 'activity' in mdata:
                if mdata['activity'].get('type', 0) == 3:
                    return True
        return False

    async def check_for_spotify(self, message):
        if message.channel.is_private or self.bot.user == message.author \
                or not isinstance(message.author, discord.Member):
            return

        server = message.server
        channel = message.channel
        if not channel.permissions_for(server.me).manage_messages:
            return
        if server.id not in self.settings:
            return
        if not self.settings[server.id]['active']:
            return
        if channel.id in self.settings[server.id]['whitelist']:
            return

        haz_spotify_embed = await self._spoti_check(message)
        if haz_spotify_embed:
            await self.bot.delete_message(message)


def setup(bot):
    pathlib.Path(path).mkdir(exist_ok=True, parents=True)
    n = AntiSpotify(bot)
    bot.add_listener(n.check_for_spotify, "on_message")
    bot.add_cog(n)
