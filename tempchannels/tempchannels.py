import os
import sys
from datetime import date, datetime, timedelta
import asyncio
import logging
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks

log = logging.getLogger('red.TempChannels')

class TempChannels:
    """
    allows creating temporary channels
    channels are auto-removed when empty
    requires server admin or manage channels to enable
    once enabled all users can use it
    """

    #todo: give the person who added the channel the Manage channel permission for that channel
    __author__ = "mikeshardmind"
    __version__ = "1.2"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/tempchannels/settings.json')

    @commands.group(name="tempchannels", aliases=["tmpc"], pass_context=True, no_pm=True)
    async def tempchannels(self, ctx):
        """Cog for allowing users to make temporary channels"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)


    def initial_config(self, server_id):
        """makes an entry for the server, defaults to turned off"""

        if server_id not in self.settings: #trust but verify
            self.settings[server_id] = {'toggle': False,
                                        'channels': [],
                                        'cache': []
                                       }
            self.save_json()

    @checks.admin_or_permissions(Manage_channels=True)
    @tempchannels.command(name="toggle", pass_context=True, no_pm=True)
    async def _tempchanneltoggle(self, ctx):
        """toggles the temp channels commands on/off for all users
        this requires the "Manage Channels" permission
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)

        if self.settings[server.id]['toggle'] is True:
            self.settings[server.id]['toggle'] = False
            self.save_json()
            await self.bot.say('Creation of temporary channels is now disabled.')
        else:
            self.settings[server.id]['toggle'] = True
            self.save_json()
            await self.bot.say('Creation of temporary channels is now enabled.')

    @tempchannels.command(name="new", pass_context=True, no_pm=True)
    async def _newtemp(self, ctx, name: str):
        """makes a new temporary channel
        channel name should be enclosed in quotation marks"""
        server = ctx.message.server
        perms = ctx.message.server.get_member(self.bot.user.id).server_permissions

        if server.id not in self.settings:
            self.initial_config(server.id)

        if perms.manage_channels is False:
            await self.bot.say('I do not have permission to do that')
        elif self.settings[server.id]['toggle'] is False:
            await self.bot.say('This command is currently turned off. Reenable with\n```{}tempchanneltoggle```'.format())
        else:
            channel = await self.bot.create_channel(server, name, type=discord.ChannelType.voice)
            self.settings[server.id]['channels'].append(channel.id)
            self.save_json()


    #Minimum permissions required to remove the channels forcefully is manage_channels
    @checks.admin_or_permissions(Manage_channels=True)
    @tempchannels.command(name="purge", pass_context=True, no_pm=True)
    async def _purgetemps(self, ctx):
        """purges this server's temp channels even if in use"""
        server = ctx.message.server


        if server.id in self.settings:
            channels = self.settings[server.id]['channels']
            for channel_id in channels:
                channel = server.get_channel(channel_id)
                if channel is not None:
                    await asyncio.sleep(0.25)
                    await self.bot.delete_channel(channel)
                    channels.remove(channel.id)
                    self.save_json()
            await self.bot.say('Temporary Channels Purged')
        else:
            await self.bot.say('No Entires for this server.')
        self.settingscleanup(server)

    @tempchannels.command(name="testing", hidden=True, pass_context=True, no_pm=True)
    async def timetesting(self,ctx):
        """hidden function for testing, should not ever exist enabled in branch master"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)

        channels = self.settings[server.id]['channels']
        cache = self.settings[server.id]['cache']

        #cleanup channels older than 5 minutes even if they haven't been entered
        for channel_id in channels:
            channel = server.get_channel(channel_id)
            if channel is not None:
                if len(server.get_channel(channel_id).voice_members) == 0:
                    timenow = datetime.utcnow()
                    ctime = sever.get_channel(channel_id).created_at()
                    await self.bot.say('The current time: ```{}``` \nCompared to when {} was created: ```{}``` '.format(timenow, channel_id, ctime))



    def save_json(self):
        dataIO.save_json("data/tempchannels/settings.json", self.settings)


    async def autoempty(self, memb_before, memb_after):
        """This cog is Self Cleaning"""
        server = memb_after.server
        channels = self.settings[server.id]['channels']
        cache = self.settings[server.id]['cache']

        #this prevents channels from being deleted before being used
        #todo: track times and prevent permanently unused channels from lasting forever.
        if memb_after.voice.voice_channel is not None:
            channel = memb_after.voice.voice_channel
            if channel.id in channels:
                if channel.id not in cache:
                    cache.append(channel.id)
                    self.save_json()

        #check to see if any temp rooms are empty when someone leaves a chat room
        channel = memb_before.voice.voice_channel
        if channel.id in cache:
            if len(channel.voice_members) == 0:
                await self.bot.delete_channel(channel)
                cache.remove(channel.id)
                channels.remove(channel.id)
                self.save_json()

        self.settingscleanup(server)


    def settingscleanup(self, server):
        """cleanup of settings in various edge cases """
        if server.id in self.settings: #can't clean a mess that doesn't exist
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



def check_folder():
    f = 'data/tempchannels'
    if not os.path.exists(f):
        os.makedirs(f)

def check_file():
    f = 'data/tempchannels/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    n = TempChannels(bot)
    bot.add_listener(n.autoempty, 'on_voice_state_update')
    bot.add_cog(n)
