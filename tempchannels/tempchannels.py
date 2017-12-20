import pathlib
from datetime import date, datetime, timedelta  # NOQA:F401
import asyncio
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks

path = 'data/tempchannels'


class TempChannels:
    """
    allows creating temporary channels
    channels are auto-removed when they become empty
    requires server admin or manage channels to enable
    once enabled all users can use it
    """
    __author__ = "mikeshardmind (Sinbad#0413)"
    __version__ = "2.0.0"

    def __init__(self, bot):
        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}

    @commands.group(name="tempchannels", aliases=["tmpc"],
                    pass_context=True, no_pm=True)
    async def tempchannels(self, ctx):
        """Make temporary channels"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @commands.group(name="tempchannelset", pass_context=True, no_pm=True)
    async def tempset(self, ctx):
        """Configuration settings for tempchannels"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    def initial_config(self, server_id):
        """makes an entry for the server, defaults to turned off"""

        if server_id not in self.settings:
            self.settings[server_id] = {'toggleactive': False,
                                        'toggleowner': False,
                                        'channels': [],
                                        'cache': []
                                        }
            self.save_json()

    @checks.admin_or_permissions(Manage_channels=True)
    @tempset.command(name="toggleactive", pass_context=True, no_pm=True)
    async def tempchanneltoggle(self, ctx):
        """toggles the temp channels commands on/off for all users
        this requires the "Manage Channels" permission
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)

        if self.settings[server.id]['toggleactive'] is True:
            self.settings[server.id]['toggleactive'] = False
            self.save_json()
            await self.bot.say('Creation of temporary '
                               'channels is now disabled.')
        else:
            self.settings[server.id]['toggleactive'] = True
            self.save_json()
            await self.bot.say('Creation of temporary '
                               'channels is now enabled.')

    @checks.admin_or_permissions(Manage_channels=True)
    @tempset.command(name="category", pass_context=True, no_pm=True)
    async def setcategory(self, ctx, category_name_or_id=None):
        """
        sets the category temporary channels are made in.
        use without a specified category to clear the settings
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if category_name_or_id is None:
            self.settings[server.id]['category'] = None
            return await self.bot.say('Category cleared')

        _id = await self.category_id_from_info(
            server, category_name_or_id)
        if _id is None:
            return await self.bot.say('No such category')

        self.settings[server.id]['category'] = _id
        self.save_json()
        await self.bot.say('Category set.')

    @checks.admin_or_permissions(Manage_channels=True)
    @tempset.command(name="toggleowner", pass_context=True, no_pm=True)
    async def toggleowner(self, ctx):
        """toggles if the creator of the temp channel owns it
        requires the "Manage Channels" permission
        Defaults to false"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)

        if self.settings[server.id]['toggleowner'] is True:
            self.settings[server.id]['toggleowner'] = False
            self.save_json()
            await self.bot.say('Users no longer own the temp '
                               'channels they make.')
        else:
            self.settings[server.id]['toggleowner'] = True
            self.save_json()
            await self.bot.say('Users now own the temp channels they make.')

    @tempchannels.command(name="new", pass_context=True, no_pm=True)
    async def newtemp(self, ctx, *, name):
        """makes a new temporary channel"""
        server = ctx.message.server
        perms = ctx.message.server.get_member(
                                           self.bot.user.id).server_permissions

        cname = str(name)

        if server.id not in self.settings:
            self.initial_config(server.id)

        if perms.manage_channels is False:
            await self.bot.say('I do not have permission to do that')
        elif self.settings[server.id]['toggleactive'] is False:
            await self.bot.say('This command is currently turned off.')
        else:
            stored_id = self.settings[server.id].get('category', None)
            parent_id = await self.category_id_from_info(server, stored_id)
            channel = await self.create_voice_channel(
                server, cname, parent_id)
            if self.settings[server.id]['toggleowner'] is True:
                overwrite = discord.PermissionOverwrite()
                overwrite.manage_channels = True
                overwrite.manage_roles = True
                await self.bot.edit_channel_permissions(
                                        channel, ctx.message.author, overwrite)
            self.settings[server.id]['channels'].append(channel.id)
            self.save_json()

    @checks.admin_or_permissions(Manage_server=True)
    @tempchannels.command(name="purge", hidden=True,
                          pass_context=True, no_pm=True)
    async def _purgetemps(self, ctx):
        """purges this server's temp channels even if in use"""
        server = ctx.message.server

        if server.id in self.settings:
            channels = self.settings[server.id]['channels']
            for channel_id in channels:
                channel = server.get_channel(channel_id)
                if channel is not None:
                    await asyncio.sleep(1)
                    await self.bot.delete_channel(channel)
                    channels.remove(channel.id)
                    self.save_json()
                await asyncio.sleep(1)
            await self.bot.say('Temporary Channels Purged')
        else:
            await self.bot.say('No Entires for this server.')
        self.settingscleanup(server)

    def save_json(self):
        dataIO.save_json("data/tempchannels/settings.json", self.settings)

    async def autoempty(self, memb_before, memb_after):
        """This cog is Self Cleaning"""
        server = memb_after.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        channels = self.settings[server.id]['channels']
        cache = self.settings[server.id]['cache']

        if memb_after.voice.voice_channel is not None:
            channel = memb_after.voice.voice_channel
            if channel.id in channels:
                if channel.id not in cache:
                    cache.append(channel.id)
                    self.save_json()

        if memb_before.server == memb_after.server:
            channel = memb_before.voice.voice_channel
            if channel is not None:
                if channel.id in cache:
                    if len(channel.voice_members) == 0:
                        await self.bot.delete_channel(channel)
                        cache.remove(channel.id)
                        channels.remove(channel.id)
                        self.save_json()
        else:
            channel = memb_before.voice.voice_channel
            if channel is not None:
                b4cache = self.settings[memb_before.server.id]['cache']
                if channel.id in b4cache:
                    if len(channel.voice_members) == 0:
                        await self.bot.delete_channel(channel)
                        cache.remove(channel.id)
                        channels.remove(channel.id)
                        self.save_json()

        for channel_id in channels:
            channel = server.get_channel(channel_id)
            if channel is not None:
                if len(server.get_channel(channel_id).voice_members) == 0:
                    tnow = datetime.utcnow()
                    ctime = server.get_channel(channel_id).created_at
                    tdelta = tnow - ctime
                    if tdelta.seconds > 300:
                        await self.bot.delete_channel(channel)
                        channels.remove(channel.id)
                        self.save_json()
                        await asyncio.sleep(1)

        self.settingscleanup(server)

    def settingscleanup(self, server):
        """cleanup of settings"""
        if server.id in self.settings:
            channels = self.settings[server.id]['channels']
            cache = self.settings[server.id]['cache']
            for channel_id in channels:
                channel = server.get_channel(channel_id)
                if channel is None:
                    channels.remove(channel_id)
                    self.save_json()
            for channel_id in cache:
                if channel_id not in channels:
                    cache.remove(channel_id)
                    self.save_json()

    async def category_id_from_info(self, server, info):
        """
        takes a server and either a snowflake or a name
        returns a matching category id, or None
        """
        data = await self.bot.http.request(
            discord.http.Route(
                'GET', '/guilds/{guild_id}/channels',
                guild_id=server.id
            )
        )
        categories = [d for d in data if d['type'] == 4]
        for cat in categories:
            if cat['id'] == info:
                return cat['id']
        for cat in categories:
            if cat['name'] == info:
                return cat['id']
        return None

    async def create_voice_channel(self, server, name, parent_id):
        payload = {
            "name": name,
            "type": 2
        }
        if parent_id is not None:
            payload["parent_id"] = parent_id

        data = await self.bot.http.request(
            discord.http.Route(
                'POST', '/guilds/{guild_id}/channels',
                guild_id=server.id), json=payload)

        return discord.Channel(server=server, **data)


def setup(bot):
    pathlib.Path(path).mkdir(exist_ok=True, parents=True)
    n = TempChannels(bot)
    bot.add_listener(n.autoempty, 'on_voice_state_update')
    bot.add_cog(n)
