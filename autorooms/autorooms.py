import os
import asyncio
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks
from discord.utils import find
from cogs.utils.chat_formatting import box, pagify


class AutoRooms:
    """
    auto spawn rooms
    """
    __author__ = "mikeshardmind"
    __version__ = "3.1"

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
                                        'toggleowner': False,
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
    async def makeclone(self, ctx, chan):
        """Takes a channel ID, turns that voice channel into a clone source"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if chan in self.settings[server.id]['channels']:
            return await self.bot.say("Channel already set.")
        if chan is not None:
            channel = find(lambda m: m.id == chan, server.channels)
            if channel is not None:
                if channel.type == discord.ChannelType.voice:
                    self.settings[server.id]['channels'].append(chan)
                    self.save_json()
                    await self.bot.say('Channel set.')
                else:
                    await self.bot.say("That isn't a voice channel.")
            else:
                await self.bot.say("No channel with that ID on this server.")
        else:
            await self.bot.send_cmd_help(ctx)

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="remclone", pass_context=True, no_pm=True)
    async def remclone(self, ctx, chan):
        """Takes a channel ID, removes that channel from the clone list"""
        server = ctx.message.server
        prefix = ctx.prefix
        if server.id not in self.settings:
            self.initial_config(server.id)
        if chan in self.settings[server.id]['channels']:
            self.settings[server.id]['channels'].remove(chan)
            self.save_json()
            await self.bot.say('Channel unset.')
        else:
            await self.bot.say("No channel with that ID currently set. "
                               "\nHint: Use {}autoroomset listclones "
                               "for a current list.".format(prefix))

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="listclones", pass_context=True, no_pm=True)
    async def listclones(self, ctx):
        """Lists the current autoroms"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)

        channels = self.settings[server.id]['channels']
        if len(channels) == 0:
            return await self.bot.say("No autorooms set for this server")

        fix_list = []
        output = "Current Auto rooms\nChannel ID: Channel Name"
        for c in channels:
            channel = find(lambda m: m.id == c, server.channels)
            if channel is None:
                fix_list.append(c)
            else:
                output += "\n{}: {}".format(c, channel.name)
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.send_message(ctx.message.author, box(page))
        for c in fix_list:
            channels.remove(c)
            self.save_json

    def save_json(self):
        dataIO.save_json("data/autorooms/settings.json", self.settings)

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="toggleowner", pass_context=True, no_pm=True)
    async def toggleowner(self, ctx):
        """toggles if the creator of the autoroom owns it
        requires the "Manage Channels" permission
        Defaults to false"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)

        if 'toggleowner' not in self.settings[server.id]:
            self.settings[server.id]['toggleowner'] = False
            # Let's avoid breaking upgrades.

        if self.settings[server.id]['toggleowner'] is True:
            self.settings[server.id]['toggleowner'] = False
            self.save_json()
            await self.bot.say('Users no longer own the autorooms '
                               ' they make.')
        else:
            self.settings[server.id]['toggleowner'] = True
            self.save_json()
            await self.bot.say('Users now own the autorooms they make.')

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="purge", pass_context=True,
                         no_pm=True, hidden=True)
    """
    removes all empty generated autorooms to assist with people intentionally
    trying to break things.
    """
    async def purge(self, ctx):
        await self._purge(ctx.message.server)
        await self.bot.say("Empty autorooms purged")

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="purgeall", pass_context=True,
                         no_pm=True, hidden=True)
    """
    removes all generated autorooms. Use with caution
    """
    async def purgeall(self, ctx):
        await self.bot.say("Warning: This will delete all cloned autorooms "
                           "whether they are in use or not. You should "
                           "probably use `{}autoroomset purge` instead. "
                           "Do you want to continue anyway? "
                           "(y/n)".format(ctx.prefix))

        message = await self.bot.wait_for_message(channel=ctx.messsage.channel,
                                                  author=ctx.messsage.author,
                                                  timeout=30)

        if message.content.lower() == "y":
            await self.bot.say("I guess you know best...")
            await self._purge(ctx.message.server, True)
            await self.bot.say("Cloned rooms purged.")
        elif message.content.lower() == "n":
            await self.bot.say("Probably for the best.")
        else:
            await self.bot.say("That was not an expected answer, "
                               "aborting purge procedure")

    async def _purge(self, server, delete_all=False):
        if server.id not in self.settings:
            return

        clones = self.settings[server.id]['clones']
        del_list = []
        for c in clones:
            channel = find(lambda m: m.id == c, server.channels)
            if channel is None:
                del_list.append(c)
            else:
                if len(channel.voice_members) == 0 or delete_all:
                    await self.bot.delete_channel(channel)
                    del_list.append(c)

        for c in del_list:
            clones.remove(c)
            self.save_json

    async def autorooms(self, memb_before, memb_after):
        """This cog is Self Cleaning"""
        server = memb_after.server
        b_server = memb_before.server
        if server.id not in self.settings and b_server.id not in self.settings:
            return
        channels = self.settings[server.id]['channels']
        cache = self.settings[server.id]['cache']
        clones = self.settings[server.id]['clones']
        b_cache = self.settings[b_server.id]['cache']

        if self.settings[server.id]['toggleactive']:
            if memb_after.voice.voice_channel is not None:
                chan = memb_after.voice.voice_channel
                if chan.id in channels:
                    overwrites = chan.overwrites
                    bit_rate = chan.bitrate
                    u_limit = chan.user_limit
                    cname = "Auto: {}".format(chan.name)
                    channel = await \
                        self.bot.create_channel(server, cname, *overwrites,
                                                type=discord.ChannelType.voice)
                    await self.bot.edit_channel(channel, bitrate=bit_rate,
                                                user_limit=u_limit)
                    await self.bot.move_member(memb_after, channel)
                    if self.settings[server.id].get('toggleowner', False):
                        # Avoids breaking upgrades
                        overwrite = discord.PermissionOverwrite()
                        overwrite.manage_channels = True
                        overwrite.manage_roles = True
                        await asyncio.sleep(0.5)
                        await self.bot.edit_channel_permissions(channel,
                                                                memb_after,
                                                                overwrite)
                    self.settings[server.id]['clones'].append(channel.id)
                self.save_json()

        if memb_after.voice.voice_channel is not None:
            channel = memb_after.voice.voice_channel
            if channel.id in clones:
                if channel.id not in cache:
                    cache.append(channel.id)
                    self.save_json()

        if memb_before.voice.voice_channel is not None:
            channel = memb_before.voice.voice_channel
            if channel.id in b_cache:
                if len(channel.voice_members) == 0:
                    await self.bot.delete_channel(channel)
                    self.settingscleanup(server)

    def settingscleanup(self, server):
        """cleanup of settings"""
        if server.id in self.settings:
            clones = self.settings[server.id]['clones']
            cache = self.settings[server.id]['cache']
            for channel_id in clones:
                channel = server.get_channel(channel_id)
                if channel is None:
                    clones.remove(channel_id)
                    self.save_json()
            for channel_id in cache:
                if channel_id not in clones:
                    cache.remove(channel_id)
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
