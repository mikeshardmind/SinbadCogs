import pathlib
import asyncio
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks
from discord.utils import find
from cogs.utils.chat_formatting import box, pagify

path = 'data/autorooms'


class AutoRooms:
    """
    auto spawn rooms
    """
    __author__ = "mikeshardmind (Sinbad#0413)"
    __version__ = "4.1.0"

    def __init__(self, bot):
        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}

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
        # backwards compatability for installs prior to 3.3
        if 'chansettings' not in self.settings[server_id]:
            self.settings[server_id]['chansettings'] = {}
        for channel in self.settings[server_id]['channels']:
            if channel not in self.settings[server_id]['chansettings']:
                self.settings[server_id]['chansettings'][channel] = \
                    {'gameroom': False,
                     'atype': None,  # None, "descrim", "author"
                     'ownership': None,  # None for default, T/F overrides
                     }
        if 'prepend' not in self.settings[server_id]:
            self.settings[server_id]['prepend'] = "Auto:"

        self.save_json()

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="setprepend", pass_context=True, no_pm=True)
    async def setprepend(self, ctx, prepend: str):
        """
        sets the prepend value for non game room autorooms
        Calling without a prepend value removes the prepend.
        The default value for this if unchanged is "Auto:"
        prepend values will be truncated if longer than 8 characters
        if you wish to include spaces, surround your prepend value with quotes
        """

        server = ctx.message.server

        self.initial_config(server.id)
        self.settings[server.id]['prepend'] = prepend[:8]
        self.save_json()
        await self.bot.say("Prepend set.")

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="channelsettings", pass_context=True, no_pm=True)
    async def setnamesettings(self, ctx, chan: str):
        """
        Interactive prompt for editing the autoroom behavior for specific
        channels
        """

        server = ctx.message.server
        ctx_channel = ctx.message.channel
        author = ctx.message.author

        self.initial_config(server.id)
        if chan is not None:
            channel = find(lambda m: m.id == chan, server.channels)
            if channel is None:
                return await self.bot.say("That doesn't appear "
                                          "to be a valid channel ID")
        if channel.id not in self.settings[server.id]['channels']:
            return await self.bot.say("That isn't an autoroom")

        await self.bot.say("Game rooms require the user joining to be playing "
                           "a game, but get a base name of the game discord "
                           "detects them playing. Game rooms also do not get"
                           "anything prepended to their name."
                           "\nIs this a game room?(y/n)")

        message = await self.bot.wait_for_message(channel=ctx_channel,
                                                  author=author, timeout=30)
        if message is None:
            await self.bot.say("I can't wait forever, lets get to the next"
                               "question.")
        elif message.clean_content.lower()[:1] == 'y':
            self.settings[server.id]['chansettings'][channel.id]['gameroom'] \
                = True
        else:
            self.settings[server.id]['chansettings'][channel.id]['gameroom'] \
                = False

        await self.bot.say("I can append values to the names of rooms in one "
                           "of a few ways. \n1. By room creator name "
                           "\n2. By user descriminator (the 4 digit "
                           "number discord displays after a username)"
                           "\n3. No appended value (this is the default)\n"
                           "Please respond with the corresponding number "
                           "to the behavior desired")

        message = await self.bot.wait_for_message(channel=ctx_channel,
                                                  author=author, timeout=30)

        if message is None:
            await self.bot.say("I can't wait forever, lets get to the next"
                               "question.")
        elif message.clean_content.lower()[:1] == '1':
            self.settings[server.id]['chansettings'][channel.id]['atype'] \
                = "author"
        elif message.clean_content.lower()[:1] == '2':
            self.settings[server.id]['chansettings'][channel.id]['atype'] \
                = "descrim"
        else:
            self.settings[server.id]['chansettings'][channel.id]['atype'] \
                = None

        await self.bot.say("There are three options for channel ownership\n"
                           "1. Use the server default\n"
                           "2. Override the default granting ownership\n"
                           "3. Override the default denying ownership\n"
                           "Please respond with the corresponding number to "
                           "the desired behavior")

        message = await self.bot.wait_for_message(channel=ctx_channel,
                                                  author=author, timeout=30)

        if message is None:
            await self.bot.say("I can't wait forever, "
                               "I am not changing this setting")
        elif message.clean_content.lower()[:1] == '2':
            self.settings[server.id]['chansettings'][channel.id]['ownership'] \
                = True
        elif message.clean_content.lower()[:1] == '3':
            self.settings[server.id]['chansettings'][channel.id]['ownership'] \
                = False
        else:
            self.settings[server.id]['chansettings'][channel.id]['ownership'] \
                = None

        self.save_json()
        await self.bot.say("Channel specific settings have been updated")

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
    @autoroomset.command(name="listautorooms", pass_context=True, no_pm=True)
    async def listclones(self, ctx):
        """Lists the current autorooms"""
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
        dataIO.save_json(path + '/settings.json', self.settings)

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
    async def purge(self, ctx):
        """
        removes all empty generated autorooms to assist with people
        intentionally trying to break things.
        """
        await self._purge(ctx.message.server)
        await self.bot.say("Empty autorooms purged")

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="purgeall", pass_context=True,
                         no_pm=True, hidden=True)
    async def purgeall(self, ctx):
        """
        removes all generated autorooms. Use with caution
        """
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

        self.initial_config(server.id)
        channels = self.settings[server.id]['channels']
        cache = self.settings[server.id]['cache']
        clones = self.settings[server.id]['clones']
        chan_settings = self.settings[server.id]['chansettings']
        if self.settings[server.id]['toggleactive']:
            if memb_after.voice.voice_channel is not None:
                chan = memb_after.voice.voice_channel
                if chan.id in channels:
                    prepend = self.settings[server.id]['prepend']
                    if chan_settings[chan.id]['gameroom']:
                        if memb_after.game is not None:
                            cname = memb_after.game.name
                        else:
                            cname = "???"
                    else:
                        cname = "{} {}".format(prepend, chan.name)
                    if chan_settings[chan.id]['atype'] is None:
                        pass
                    elif chan_settings[chan.id]['atype'] == "author":
                        cname += " {0.display_name}".format(memb_after)
                    elif chan_settings[chan.id]['atype'] == "descrim":
                        cname += " {0.discriminator}".format(memb_after)

                    channel = await self._clone_channel(chan, cname)
                    await self.bot.move_member(memb_after, channel)

                    ownership = chan_settings[chan.id]['ownership']
                    if ownership is None:
                        ownership = self.settings[server.id].get('toggleowner',
                                                                 False)
                    if ownership:
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

        if b_server.id in self.settings:
            b_cache = self.settings[b_server.id]['cache']
            if memb_before.voice.voice_channel is not None:
                channel = memb_before.voice.voice_channel
                if channel.id in b_cache:
                    if len(channel.voice_members) == 0:
                        await self.bot.delete_channel(channel)
                        self.settingscleanup(b_server)

    async def _clone_channel(self, origin, new_name):
        """I can support channel categories"""
        data = await self.bot.http.request(
            discord.http.Route(
                'GET', '/guilds/{guild_id}/channels',
                guild_id=origin.server.id))
        keys = ['type',
                'bitrate',
                'user_limit',
                'permission_overwrites',
                'parent_id',
                'nsfw']
        channeldata = [d for d in data if d['id'] == origin.id][0]
        payload = {k: v for k, v in channeldata.items() if k in keys}
        payload['name'] = new_name
        new_channeldata = await \
            self.bot.http.request(
                discord.http.Route(
                    'POST', '/guilds/{guild_id}/channels',
                    guild_id=origin.server.id), json=payload)
        return discord.Channel(server=origin.server, **new_channeldata)

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


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = AutoRooms(bot)
    bot.add_listener(n.autorooms, 'on_voice_state_update')
    bot.add_cog(n)
