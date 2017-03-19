import os
import sys
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
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/tempchannels/settings.json')

    @checks.admin_or_permissions(Manage_channels=True)
    @commands.group(pass_context=True, no_pm=True)
    async def tempchanneltoggle(self, ctx):
        """toggles the temp channels commands on/off for all users
        this requires the "Manage Channels" permission
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {'toggle': True,
                                        'channels': [],
                                        'cache': []
                                       }
            self.save_json()
            await self.bot.say('Creation of temporary channels is now enabled.')
        elif server.id in self.settings:
            if self.settings[server.id]['toggle'] is True:
                self.settings[server.id]['toggle'] = False
                self.save_json()
                await self.bot.say('Creation of temporary channels is now disabled.')
            else:
                self.settings[server.id]['toggle'] = True
                self.save_json()
                await self.bot.say('Creation of temporary channels is now enabled.')

    @commands.group(pass_context=True, no_pm=True)
    async def newtemp(self, ctx, name: str):
        """makes a new temporary channel
        channel name should be enclosed in quotation marks"""
        server = ctx.message.server
        perms = ctx.message.server.get_member(self.bot.user.id).server_permissions

        if perms.manage_channels is False:
            await self.bot.say('I do not have permission to do that')
        elif self.settings[server.id]['toggle'] is False:
            await self.bot.say('This command is currently turned off. Reenable with\n```[p]tempchanneltoggle```')
        else:
            channel = await self.bot.create_channel(server, name, type=discord.ChannelType.voice)
            self.settings[server.id]['channels'].append(channel.id)
            self.save_json()


    #Minimum permissions required to remove the channels forcefully is manage_channels
    @checks.admin_or_permissions(Manage_channels=True)
    @commands.group(pass_context=True, no_pm=True)
    async def purgetemps(self, ctx):
        """purges this server's temp channels even if in use"""
        server = ctx.message.server

        for channel_id in self.settings[server.id]['channels']:
            try:
                channel = server.get_channel(channel_id)
                await asyncio.sleep(0.25)
                await self.bot.delete_channel(channel)
                await self.bot.say('Temporary Channels Purged')
            except:
                e = sys.exc_info()[0]
                log.debug('Exception During purgetemps: ' +str(e))
                pass

            self.settings[server.id]['channels'].clear()
            self.save_json()


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

        #cleanup cache in cases I have yet to figure out why they occur rarely
        for channel_id in cache:
            if channel_id not in channels:
                cache.remove(channel_id)

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
