import os
import sys  # noqa: F401
from datetime import date, datetime, timedelta  # noqa: F401
import asyncio
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks


class AutoRooms:
    """
    auto spawn rooms
    """
    __author__ = "mikeshardmind"
    __version__ = "2.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/autorooms/settings.json')

    @commands.group(name="autoroomset", pass_context=True, no_pm=True)
    async def autoroomset(self, ctx):
        """Configuration settings for AutoRooms"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    def initial_config(self, server_id):
        """makes an entry for the server, defaults to turned off"""

        if server_id not in self.settings:
            self.settings[server_id] = {'toggleactive': False,
                                        'channels': [],
                                        'clones': [],
                                        'cache': []
                                        }
            self.save_json()

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="toggleactive", pass_context=True, no_pm=True)
    async def autoroomtoggle(self, ctx):
        """
        turns autorooms on and off
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)

        if self.settings[server.id]['toggleactive'] is True:
            self.settings[server.id]['toggleactive'] = False
            self.save_json()
            await self.bot.say('Auto Rooms disabled.')
        else:
            self.settings[server.id]['toggleactive'] = True
            self.save_json()
            await self.bot.say('Auto Rooms enabled.')

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="makeclone", pass_context=True, no_pm=True)
    async def settrigger(self, ctx, chan):
        """Takes a channel ID, turns that voice channel into a clone source"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if chan is not None:
            self.settings[server.id]['channels'].append(chan)
            self.save_json()
            await self.bot.say('channel set')

    def save_json(self):
        dataIO.save_json("data/autorooms/settings.json", self.settings)

    async def autorooms(self, memb_before, memb_after):
        """This cog is Self Cleaning"""

        server_after = memb_after.server
        if server_after is not None:
            sa_channels = self.settings[server_after.id]['channels']
            sa_cache = self.settings[server_after.id]['cache']
            sa_clones = self.settings[server_after.id]['clones']

        server_before = memb_before.server
        if server_before is not None:
            sb_channels = self.settings[server_before.id]['channels']
            sb_cache = self.settings[server_before.id]['cache']
            sb_clones = self.settings[server_before.id]['clones']

        if self.settings[server.id]['toggleactive']:
            if memb_after.voice.voice_channel is not None:
                chan = memb_after.voice.voice_channel
                if chan.id in sa_channels:
                    overwrites = chan.overwrites
                    cname = "Auto: {}".format(chan.name)
                    channel = await self.bot.create_channel(
                            server, cname, type=discord.ChannelType.voice)
                    for overwrite in overwrites:
                        await self.bot.edit_channel_permissions(channel,
                                                                overwrite)
                    await self.bot.move_member(memb_after, channel)
                    sa_clones.append(channel.id)
                    self.save_json()

        if memb_after.voice.voice_channel is not None:
            channel = memb_after.voice.voice_channel
            if channel.id in sa_clones:
                if channel.id not in sa_cache:
                    sa_cache.append(channel.id)
                    self.save_json()

        if memb_before.voice.voice_channel is not None:
            channel = memb_before.voice.voice_channel
            if channel.id in sb_cache:
                if len(channel.voice_members) == 0:
                    await self.bot.delete_channel(channel)
                    sb_clones.remove(channel.id)
                    sb_cache.remove(channel.id)
                    self.save_json()


def check_folder():
    f = 'data/autorooms'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/autorooms/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = AutoRooms(bot)
    bot.add_listener(n.autorooms, 'on_voice_state_update')
    bot.add_cog(n)
