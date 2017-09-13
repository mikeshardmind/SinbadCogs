#  with apologies to Will for butchering his scheduler code to make this work
#  scheduler found here:
#  https://github.com/tekulvw/Squid-Plugins/blob/master/scheduler/scheduler.py

import discord
from discord.ext import commands
from cogs.utils import checks, snowflake_time
from cogs.utils.dataIO import dataIO
import logging
import os
import asyncio
import time
import datetime
import random
from typing import Union
import string
assert datetime  # pyflakes grr

log = logging.getLogger("red.TempText")

creationmessage = "Hi {0.mention}, I've created your channel here. " \
                  "People eligible to join can do so by using the following " \
                  "command.\n`{1}jointmptxt {2.id}`"
# author, prefix, channel


class TmpTxtError(Exception):
    pass


class TempTextChannel:

    def __init__(self, data):
        self.channel = data.pop('channel')
        self.server = data.pop('server')
        self.owner = data.pop('owner')
        self.timedelta = data.pop('timedelta')
        self.createdat = data.pop('createdat')
        self.rid = data.pop('rid')

    def __lt__(self, other):
        my_sig = "{}-{}-{}-{}".format(self.timedelta, self.name,
                                      self.createdat, self.channel)
        other_sig = "{}-{}-{}-{}".format(other.timedelta, other.name,
                                         other.createdat, other.channel)
        return hash(my_sig) < hash(other_sig)


class TempText:

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/temptext/settings.json')
        self.channels = dataIO.load_json('data/temptext/channels.json')
        self.queue = asyncio.PriorityQueue(loop=self.bot.loop)
        self.queue_lock = asyncio.Lock()
        self.to_kill = {}
        self._load()

    def save_settings(self):
        dataIO.save_json("data/temptext/settings.json", self.settings)

    def save_channels(self):
        dataIO.save_json("data/temptext/channels.json", self.embeds)

    def _parse_time(self, time):
        translate = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        timespec = time[-1]
        if timespec.lower() not in translate:
            raise ValueError
        timeint = int(time[:-1])
        return timeint * translate.get(timespec)

    @checks.serverowner()
    @commands.command(name="tmptxtdeletion", hidden=True,
                      no_pm=True, pass_context=True)
    async def _never_run_this_manually(self, ctx, channelid: str):
        """
        I swear to fucking god if you run this manually,
        you are an idiot. Just delete it manually, you certainly have
        permission to do so as server owner.
        """
        try:
            channel = self.bot.get_channel(channelid)
            server = channel.server
        except AttributeError:
            log.debug("Not deleting channel that doesn't exist")

        if server != ctx.channel.server:
            log.debug("You should never get this error")
            return

        if channel.permissions_for(server.me).manage_channel:
            try:
                await self.bot.delete_channel(channel)
            except Exception as e:
                log.debug("{}".format(e))
                content = "Hey {0.mention}, something went wrong and this " \
                          "channel wasn't unmade as scheduled"
                try:
                    await self.bot.send_message(channel, content)
                except Exception as e:
                    log.debug("{}".format(e))
        else:
            output = "Hey dumbass. Yes you, {0.mention} . I can't delete " \
                     "temporary channels if you remove my ability to manage " \
                     "channels. I'll be nice and tell you it occured in " \
                     "{1.name} dealing with this channel {2.mention}" \
                     "".format(server.owner, server, channel)
            try:
                await self.bot.send_message(server.owner, output)
            except Exception as e:
                try:
                    await self.bot.send_message(channel, output)
                except Exception:
                    log.debug("Oh fuck you {0.id} || {0.name}"
                              " owner of {1.id} || {1.name}"
                              "".format(server.owner, server))

    def run_coro(self, tmptxt: TempTextChannel):
        channel = self.bot.get_channel(tmptxt.channel)
        try:
            server = channel.server
            prefix = self.bot.settings.get_prefixes(server)[0]
        except AttributeError:
            log.debug("Channel no longer found, not attempting to delete it")
            return
        data = {}
        data['timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())
        data['id'] = random.randint(10**(17), (10**18) - 1)
        data['content'] = prefix + "tmptxtdeletion " + tmptxt.channel
        data['channel'] = self.bot.get_channel(tmptxt.channel)
        data['author'] = {'id': server.owner.id}
        data['nonce'] = random.randint(-2**32, (2**32) - 1)
        data['channel_id'] = tmptxt.channel
        data['reactions'] = []
        utility_message = discord.Message(**data)
        self.bot.dispatch('message', utility_message)

    def _load(self):
        for server in self.channels:
            for chanid, tmptxt in self.channels[server].items():
                t = TempTextChannel(tmptxt)
                self.bot.loop.create_task(self._schedule_deletion(t))

    async def _schedule_deletion(self, tmptxt: TempTextChannel):

        when = tmptxt.createdat + tmptxt.timedelta
        await self.queue.put((when, tmptxt))

    async def _make_scheduled_deletion(self, channel: discord.Channel,
                                       owner: discord.Member,
                                       timedelta, rid=None):

        if channel.server.id not in self.channels:
            self.channels[channel.server.id] = {}

        cd = {'server': channel.server.id,
              'channel': channel.id,
              'owner': owner.id,
              'timedelta': timedelta,
              'createdat': time.mktime(snowflake_time(channel.id).timetuple()),
              'rid': rid
              }

        self.channels[channel.server.id][channel.id] = cd.copy()

        t = TempTextChannel(cd.copy())
        await self._schedule_deletion(t)
        self.save_channels()

    @commands.command(pass_context=True, name="tmptxt")
    async def _scheduler_add(self, ctx, time_interval: str, name: str,
                             role: discord.Role=None):
        """
        Makes a channel to be deleted in [time_interval].
        Time format: 1s, 2m, 3h, 5d, 1w
        Optionally set a role requirement to be allowed to join the channel
        """

        author = ctx.message.author
        if not self._is_allowed(author):
            return
        try:
            x = await self._process_temp(ctx.prefix, author,
                                         time_interval, name, role)
        except TmpTxtError as e:
            await self.bot.say("{}".format(e))
        else:
            await self.bot.say("Channel made -> {0.mention}".format(x))

    async def _process_temp(self, prefix, author,
                            time_interval, unproxnm, rid=None):
        server = author.server
        unproxnm = unproxnm.lower()

        name = "".join(ch for ch in unproxnm if ch.isalpha())
        try:
            seconds = self._parse_time(time_interval)
        except ValueError:
            raise TmpTxtError("Time format: 2m, 3h, 5d, 1w ")
            return

        if not self.is_valid_interval(server, seconds):
            raise TmpTxtError("That time was not within the valid range "
                              "for this server")
            return
        if len(name) == 0:
            name = ''.join([random.choice(string.ascii_letters)
                            for n in range(12)])

        if server.me.server_permissions.manage_channels:
            try:
                base_perms = discord.PermissionOverwrite(read_messages=False)
                joined_perms = discord.PermissionOverwrite(read_messages=True)
                x = await self.bot.create_channel(server, name,
                                                  (server.default_role,
                                                   base_perms),
                                                  (server.me, joined_perms),
                                                  (author, joined_perms))
            except Exception as e:
                log.debug("{}".format(e))
                raise TmpTxtError("I ran into an unexpected error")
                return
        else:
            raise TmpTxtError("I don't have permission to do that")
            return
        try:
            await self.bot.send_message(x, creationmessage.format(author,
                                                                  prefix, x))
        except Exception:
            pass  # I really don't care if this fails
        await self._make_scheduled_deletion(x, author, seconds, rid)

    def _is_allowed(self, author: discord.Member, chan_id=None):
        server = author.server
        if server.id not in self.settings:
            return False
        if not self.settings[server.id].get('active', False):
            return False
        if self._is_ignored(author):
            return False
        if chan_id is not None:
            rid = self.channels[server.id][chan_id].get('rid', None)
            if rid is not None:
                role = [r for r in server.roles if r.id == rid][0]
                if role not in author.roles:
                    return False
        rid = self.settings[server.id].get('role', None)
        if rid is not None:
            role = [r for r in server.roles if r.id == rid][0]
            if self.settings[server.id].get('strictrole', True):
                return role in author.roles
            else:
                return author.top_role >= role

    def _is_ignored(self, author: Union[discord.Member, discord.Role]):
        ignored = self.settings[author.server.id].get('ignored', [])
        if author.id in ignored:
            return True
        if isinstance(author, discord.Member):
            for role in author.roles:
                if self._is_ignored(role):
                    return True
        return False

    async def _manager(self):
        while self == self.bot.get_cog('TempText'):
            await self.queue_lock.acquire()
            if self.queue.qsize() != 0:
                curr_time = int(time.time())
                next_tuple = await self.queue.get()
                next_time = next_tuple[0]
                next_del = next_tuple[1]
                diff = next_time - curr_time
                diff = diff if diff >= 0 else 0
                if diff < 30:
                    fut = self.bot.loop.call_later(diff, self.run_coro,
                                                   next_del)
                    self.to_kill[next_time] = fut
                    del self.channels[next_del.server][next_del.channel]
                    self.save_channels()
                else:
                    await self._put_event(next_del, next_time)
            self.queue_lock.release()

            to_delete = []
            for start_time, old_chan in self.to_kill.items():
                if time.time() > start_time + 30:
                    old_chan.cancel()
                    to_delete.append(start_time)
            for item in to_delete:
                del self.to_kill[item]

            await asyncio.sleep(5)
        while self.queue.qsize() != 0:
            await self.queue.get()
        while len(self.to_kill) != 0:
            curr = self.to_kill.pop()
            curr.cancel()


def check_folder():
    f = 'data/temptext'
    if not os.path.exists(f):
        os.makedirs(f)


def check_files():
    f = 'data/temptext/channels.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})
    f = 'data/temptext/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_files()
    n = TempText(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n._manager())
    bot.add_cog(n)
