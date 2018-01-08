import pathlib
import asyncio
from datetime import datetime, timedelta
import logging

import discord
from discord.ext import commands

from cogs.utils.dataIO import dataIO
from .utils import checks
from cogs.utils.chat_formatting import box, pagify

path = 'data/autorooms'
log = logging.getLogger('red.autorooms')
log.setlevel(logging.INFO)


class AutoRoom:
    """
    Utility class
    """

    def __init__(self, **kwargs):
        self.owner_id = kwargs.get('owner_id')
        self.channel = kwargs.get('channel')
        self.id = kwargs.get('channel').id

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
        return len(self._channel.voice_members) == 0

    @property
    def should_delete(self):
        return self.is_empty and \
            (self._channel.created_at + timedelta(seconds=2)) \
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
                # Backwards Compatability pre 5.0.0
                if isinstance(entry, str):
                    channel_id, owner_id = entry, None
                else:
                    channel_id, owner_id = entry
                channel = self.bot.get_channel(channel_id)
                if channel is None:
                    rem_list.append(entry)
                    continue
                ar = AutoRoom(channel=channel, owner_id=owner_id)
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

        vc_after = memb_after.voice.voice_channel
        if vc_after.id in self.settings[vc_after.server.id]['channels'] \
                and self.settings[vc_after.server.id]['toggleactive']:
            await self._room_for(memb_after)

        if memb_before.server.id in self.settings:
            await self._cleanup(memb_before.server)

    async def _room_for(self, member: discord.Member):
        server = member.server
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
        chan_settings = self.settings[server.id]['chansettings']
        if chan_settings[chan.id]['gameroom']:
            if member.game is not None:
                cname = member.game.name
            else:
                cname = "???"
        else:
            prepend = self.settings[server.id]['prepend']
            if chan_settings[chan.id]['atype'] is None:
                append = ""
            elif chan_settings[chan.id]['atype'] == "author":
                append = " {0.display_name}".format(member)
            elif chan_settings[chan.id]['atype'] == "descrim":
                append = " {0.discriminator}".format(member)
            
            cname = "{}{}{}".format(
                prepend, chan.name, append
            )

        ownership = chan_settings[chan.id]['ownership']
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
            await self.bot.move_member(member, channel)
        except Exception as e:
            log.exception(e)
        else:
            self._antispam[member.id].stamp()
            self.settings[server.id]['clones'].append(channel.id)
            self.save_json()

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


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = AutoRooms(bot)
    bot.add_listener(n._autorooms, 'on_voice_state_update')
    bot.add_cog(n)
