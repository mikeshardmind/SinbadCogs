import pathlib
from datetime import datetime, timedelta
import logging

import discord
from discord.ext import commands

from cogs.utils.dataIO import dataIO
from .utils import checks
from cogs.utils.chat_formatting import box, pagify

path = 'data/autorooms'
log = logging.getLogger('red.autorooms')


class AutoRoom:
    """
    Utility class
    subclassing discord.Channel seems excessive
    """

    def __init__(self, **kwargs):
        self.channel = kwargs.get('channel')
        self.id = kwargs.get('channel').id

    # implementing __eq__ , __ne__, and __hash__ like this
    # to allow list/set membership checks to be done lazily
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.channel.id == other.channel.id
        elif isinstance(other, discord.Channel):
            return self.channel.id == other.id
        return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.channel.id != other.channel.id
        elif isinstance(other, discord.Channel):
            return self.channel.id != other.id
        return True

    def __hash__(self):
        return hash(self.channel.id)

    @property
    def is_empty(self):
        return len(self.channel.voice_members) == 0

    @property
    def should_delete(self):
        return self.is_empty and \
            (self.channel.created_at + timedelta(seconds=2)) \
            < datetime.utcnow()


class AutoRoomAntiSpam:
    """
    Because people are jackasses
    """

    def __init__(self):
        self.event_timestamps = []

    def _interval_check(self, interval: timedelta, threshold: int):
        return len(
            [t for t in self.event_timestamps
             if (t + interval) > datetime.utcnow()]
        ) >= threshold

    @property
    def spammy(self):
        return self._interval_check(timedelta(seconds=5), 1) \
            or self._interval_check(timedelta(minutes=1), 3)

    def stamp(self):
        self.event_timestamps.append(datetime.utcnow())
        # This is to avoid people abusing the bot to get
        # it ratelimited. We don't care about anything older than
        # 1 hour, so we can discard those events
        self.event_timestamps = [
            t for t in self.event_timestamps
            if t + timedelta(hours=1) > datetime.utcnow()
        ]


class AutoRooms:
    """
    auto spawn rooms
    """
    __author__ = "mikeshardmind (Sinbad#0413)"
    __version__ = "5.0.0"

    def __init__(self, bot: commands.bot):
        self.bot = bot
        self._rooms = []  # List[AutoRoom]
        self._antispam = {}  # user_id -> AutoRoomAntiSpam
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}
        self._resume()

    def save_json(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    def _resume(self):
        """
        handle getting state info on cog load
        """
        for server_id in self.settings:
            rem_list = []
            server = self.bot.get_server(server_id)
            if server is None:
                continue
            for entry in self.settings[server.id]['clones']:
                channel = self.bot.get_channel(entry)
                if channel is None:
                    rem_list.append(entry)
                    continue
                ar = AutoRoom(channel=channel)
                self._rooms.append(ar)
            self.settings[server.id]['clones'] = [
                entry for entry in self.settings[server.id]['clones']
                if entry not in rem_list
            ]

    async def _clone_channel(
            self, origin: discord.Channel, new_name: str, *overwrites):
        """
        Channel categories don't exist in discord.py 0.16

        This isn't an ideal way of doing this, but to support
        channel categories on 0.16, I don't have many other
        options for doing it.
        """
        # The good news is this function doesn't need to be ported to
        # the rewrite version of the cog
        data = await self.bot.http.request(
            discord.http.Route(
                'GET', '/guilds/{guild_id}/channels',
                guild_id=origin.server.id))
        keys = [
            'type',
            'bitrate',
            'user_limit',
            'permission_overwrites',
            'parent_id',
            'nsfw'
        ]
        channeldata = [d for d in data if d['id'] == origin.id][0]
        payload = {k: v for k, v in channeldata.items() if k in keys}
        if len(overwrites) > 0:
            for overwrite in overwrites:
                target, perm = overwrite
                allow, deny = perm.pair()
                o_data = {
                    'allow': allow.value,
                    'deny': deny.value,
                    'id': target.id,
                    'type': type(target).__name__.lower()
                    }
                payload['permission_overwrites'] = [
                    o for o in payload['permission_overwrites']
                    if o['id'] != o_data['id']
                ]
                payload['permission_overwrites'].append(o_data)
        payload['name'] = new_name
        new_channeldata = await \
            self.bot.http.request(
                discord.http.Route(
                    'POST', '/guilds/{guild_id}/channels',
                    guild_id=origin.server.id), json=payload)
        return discord.Channel(server=origin.server, **new_channeldata)

    async def _autorooms(self, memb_before: discord.Member,
                         memb_after: discord.Member):
        """
        Detect voice state changes, and call the appropriate functions
        based on the change
        """

        if memb_after.voice.voice_channel == memb_before.voice.voice_channel:
            # We don't care if the channel they are in hasn't changed
            return

        try:
            if memb_after.server.id in self.settings:
                vc_after = memb_after.voice.voice_channel
                if vc_after.id in \
                        self.settings[vc_after.server.id]['channels'] \
                        and self.settings[vc_after.server.id]['toggleactive']:
                    await self._room_for(memb_after)
        except AttributeError:
            # 4-deep if nesting for None checking or this
            pass

        if memb_before.server is not None:
            if memb_before.server.id in self.settings:
                await self._cleanup(memb_before.server)

    async def _room_for(self, member: discord.Member):
        server = member.server
        self.initial_config(server.id)
        if not (server.me.server_permissions.manage_channels
                and server.me.server_permissions.move_members):
            return
        if member.id not in self._antispam:
            self._antispam[member.id] = AutoRoomAntiSpam()
        if self._antispam[member.id].spammy:
            log.info("{0.id} | {0.display_name} "
                     "has triggered the antispam catcher".format(member))
            return
        chan = member.voice.voice_channel
        chan_settings = {
            'gameroom': False,
            'atype': None,
            'ownership': None
        }
        if chan.id in self.settings[server.id]['chansettings']:
            chan_settings = \
                self.settings[server.id]['chansettings'].get(chan.id)
        if chan_settings['gameroom']:
            if member.game is not None:
                cname = member.game.name
            else:
                cname = "???"
        else:
            prepend = self.settings[server.id]['prepend']
            if chan_settings['atype'] is None:
                append = ""
            elif chan_settings['atype'] == "author":
                append = " {0.display_name}".format(member)
            elif chan_settings['atype'] == "descrim":
                append = " {0.discriminator}".format(member)

            cname = "{}{}{}".format(
                prepend, chan.name, append
            )

        ownership = chan_settings['ownership']
        overwrite = discord.PermissionOverwrite()
        if ownership is None:
            ownership = self.settings[server.id].get(
                'toggleowner', False
            )
        if ownership:
            overwrite.manage_channels = True
            overwrite.manage_roles = True

        try:
            channel = await self._clone_channel(
                chan, cname, (member, overwrite)
            )
        except Exception as e:
            log.exception(e)
        else:
            self.settings[server.id]['clones'].append(channel.id)
            self.save_json()
            self._antispam[member.id].stamp()
            self._rooms.append(AutoRoom(channel=channel))
            try:
                await self.bot.move_member(member, channel)
            except Exception as e:
                log.exception(e)

    async def _cleanup(self, server: discord.Server):
        channels = [
            ar.channel for ar in self._rooms
            if ar.should_delete
            and ar.channel.server == server
        ]
        ids = []
        if not server.me.server_permissions.manage_channels:
            return
        for channel in channels:
            _id = channel.id
            try:
                await self.bot.delete_channel(channel)
            except Exception as e:
                log.exception(e)
            else:
                ids.append(_id)

        self._rooms = [ar for ar in self._rooms if ar.id not in ids]

    def initial_config(self, server_id):
        """makes an entry for the server, defaults to turned off"""

        if server_id not in self.settings:
            self.settings[server_id] = {}
        default_data = {'toggleactive': False,
                        'toggleowner': False,
                        'channels': [],
                        'clones': [],
                        'chansettings': {},
                        'prepend': "Auto: "}
        self.settings[server_id].update(
            {k: v for k, v in default_data.items()
             if k not in self.settings[server_id]}
        )

    # commands
    @commands.group(name="autoroomset", pass_context=True, no_pm=True)
    async def autoroomset(self, ctx):
        """Configuration settings for AutoRooms"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="prepend", pass_context=True, no_pm=True)
    async def setprepend(self, ctx, prepend: str=""):
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
    async def setchannelsettings(self, ctx, channel: discord.Channel):
        """
        Interactive prompt for editing the autoroom behavior for specific
        channels
        """

        server = ctx.message.server
        ctx_channel = ctx.message.channel
        author = ctx.message.author

        self.initial_config(server.id)
        if channel.id not in self.settings[server.id]['channels']:
            return await self.bot.say("That isn't an autoroom")
        if channel.id not in self.settings[server.id]['chansettings']:
            self.settings[server.id]['chansettings'][channel.id] = {
                'gameroom': False,
                'atype': None,
                'ownership': None
            }

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
            [channel.id]['ownership'] \
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
            await self.bot.say('Auto Rooms disabled.')
        else:
            self.settings[server.id]['toggleactive'] = True
            await self.bot.say('Auto Rooms enabled.')
        self.save_json()

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="makeclone", pass_context=True, no_pm=True)
    async def makeclone(self, ctx, channel: discord.Channel):
        """Takes a channel, turns that voice channel into a clone source"""
        server = ctx.message.server
        if server != channel.server:
            log.info(
                "{0.id} | {0.name} just tried to make an autoroom"
                "for a channel in another server"
            )
            return
        if server.id not in self.settings:
            self.initial_config(server.id)
        if channel.id in self.settings[server.id]['channels']:
            return await self.bot.say("Channel already set.")
        if channel.type == discord.ChannelType.voice:
            self.settings[server.id]['channels'].append(channel.id)
            self.save_json()
            await self.bot.say('Channel set.')
        else:
            await self.bot.say("That isn't a voice channel.")

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="remclone", pass_context=True, no_pm=True)
    async def remclone(self, ctx, channel: discord.Channel):
        """Takes a channel, removes that channel from the clone list"""
        server = ctx.message.server
        prefix = ctx.prefix
        if server.id not in self.settings:
            self.initial_config(server.id)
        if channel.id in self.settings[server.id]['channels']:
            self.settings[server.id]['channels'].remove(channel.id)
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
            channel = discord.utils.find(
                lambda m: m.id == c, server.channels
            )
            if channel is None:
                fix_list.append(c)
            else:
                output += "\n{}: {}".format(c, channel.name)
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.send_message(ctx.message.author, box(page))
        for c in fix_list:
            channels.remove(c)
            self.save_json

    @checks.admin_or_permissions(Manage_channels=True)
    @autoroomset.command(name="toggleowner", pass_context=True, no_pm=True)
    async def toggleowner(self, ctx):
        """toggles if the creator of the autoroom owns it
        requires the "Manage Channels" permission
        Defaults to false"""
        server = ctx.message.server
        self.initial_config(server.id)

        if self.settings[server.id]['toggleowner'] is True:
            self.settings[server.id]['toggleowner'] = False
            self.save_json()
            await self.bot.say('Users no longer own the autorooms '
                               ' they make.')
        else:
            self.settings[server.id]['toggleowner'] = True
            self.save_json()
            await self.bot.say('Users now own the autorooms they make.')


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = AutoRooms(bot)
    bot.add_listener(n._autorooms, 'on_voice_state_update')
    bot.add_cog(n)
