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

    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/temptext/settings.json')
        self.channels = dataIO.load_json('data/temptext/channels.json')
        self.queue = asyncio.PriorityQueue(loop=self.bot.loop)
        self.queue_lock = asyncio.Lock()
        self.to_kill = {}
        self._load()

    def update_settings(self, server: discord.Server, data=None):
        if server.id not in self.settings:
            self.settings[server.id] = {'active': False,
                                        'ignored': [],  # Future feature
                                        'rid': None,
                                        'strict': True,
                                        'schan_limit': 50,  # Future feature
                                        'uchan_limit': 2,  # Future feature
                                        'min_time': 1800,  # 30m in s
                                        'max_time': 604800,  # 1w in s
                                        'default_time': 10800  # 3h in s
                                        }
        if data is not None:
            self.settings[server.id].update(data)
        self.save_settings()

    def save_settings(self):
        dataIO.save_json("data/temptext/settings.json", self.settings)

    def save_channels(self):
        dataIO.save_json("data/temptext/channels.json", self.channels)

    def _parse_time(self, time):
        translate = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
        timespec = time[-1]
        if timespec.lower() not in translate:
            raise ValueError
        timeint = int(time[:-1])
        return timeint * translate.get(timespec)

    @checks.admin_or_permissions(manage_server=True)
    @commands.group(name="tmptxtset", pass_context=True, no_pm=True)
    async def tmptxtset(self, ctx):
        """configuration settings for temporary temp channels"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @tmptxtset.command(name="toggleactive", pass_context=True, no_pm=True)
    async def toggleactive(self, ctx):
        """
        toggles it on/off
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.update_settings(server)

        active = not self.settings[server.id]['active']
        self.update_settings(server, {'active': active})
        await self.bot.say("Active: {}".format(active))

    @tmptxtset.command(name="togglestrict", pass_context=True, no_pm=True)
    async def togglestrict(self, ctx):
        """
        toggles strict role checking on/off
        when off, the required role or any above it will work
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.update_settings(server)

        strict = not self.settings[server.id]['strict']
        self.update_settings(server, {'strict': strict})
        await self.bot.say("Strict mode: {}".format(strict))

    @tmptxtset.command(name="defaultime", pass_context=True, no_pm=True)
    async def setdefaulttime(self, ctx, default_time):
        """
        sets the time used for autotxt
        times should be between 30 minutes and 1 week
        Time format: 30m, 3h, 5d, 1w
        default is 3h
        """
        try:
            seconds = self._parse_time(default_time)
        except ValueError:
            return await self.bot.send_cmd_help(ctx)

        if not self._is_valid_interval(seconds):
            return await self.bot.send_cmd_help(ctx)

        self.update_settings(ctx.message.server, {'default_time': seconds})
        await self.bot.say("Default set")

    @tmptxtset.command(name="validtimerange", pass_context=True, no_pm=True)
    async def setvalidtimerange(self, ctx, min_time, max_time):
        """
        times should be between 30 minutes and 1 week
        Time format: 30m, 3h, 5d, 1w
        """
        try:
            min_seconds = self._parse_time(min_time)
        except ValueError:
            return await self.bot.send_cmd_help(ctx)
        try:
            max_seconds = self._parse_time(max_time)
        except ValueError:
            return await self.bot.send_cmd_help(ctx)

        if (not self._is_valid_interval(min_seconds)) or \
                (not self._is_valid_interval(max_seconds)):
            return await self.bot.send_cmd_help(ctx)

        if min_seconds > max_seconds:
            await self.bot.say("You dun goofed. Swapping your min and max "
                               "so that the smaller of the two is the minimum")
            min_seconds, max_seconds = max_seconds, min_seconds

        self.update_settings(ctx.message.server, {'min_time': min_seconds,
                                                  'max_time': max_seconds})

        await self.bot.say("Times set")

    @tmptxtset.command(name="requiredrole", pass_context=True, no_pm=True)
    async def setrequiredrole(self, ctx, role: discord.Role=None):
        """
        sets the required role this can be set as the lowest role required
        rather than a strict requirement
        clear setting by using without a role
        """

        rid = None
        if role is not None:
            rid = role.id

        self.update_settings(ctx.message.server, {'rid': rid})
        await self.bot.say("Settings updated.")

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

    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.command(pass_context=True, name="autotxt")
    async def _quick_add(self, ctx):
        """
        Makes a temp channel using the automatic time settings
        """

        author = ctx.message.author
        if not self._is_allowed(author):
            return
        time_interval = self.settings[author.server.id]['default_time']
        try:
            x = await self._process_temp(ctx.prefix, author,
                                         time_interval, "1111")
        except TmpTxtError as e:
            await self.bot.say("{}".format(e))
        else:
            await self.bot.say("Channel made -> {0.mention}".format(x))

    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.command(pass_context=True, name="tmptxt")
    async def _temp_add(self, ctx, time_interval: str, name: str,
                        role: discord.Role=None):
        """
        Makes a temp channel to be deleted in [time_interval].
        Time format: 30m, 3h, 5d, 1w
        Optionally set a role requirement to be allowed to join the channel
        """

        author = ctx.message.author
        if not self._is_allowed(author):
            return
        if role is not None:
            rid = role.id
        else:
            rid = None
        try:
            x = await self._process_temp(ctx.prefix, author,
                                         time_interval, name, rid)
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
            raise TmpTxtError("Time format: 30m, 3h, 5d, 1w ")
            return

        if not self._is_valid_interval(seconds, server):
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
        if self._at_channel_limit(author):
            return False
        if chan_id is not None:
            rid = self.channels[server.id][chan_id].get('rid', None)
            if rid is not None:
                role = [r for r in server.roles if r.id == rid][0]
                if role not in author.roles:
                    return False
        rid = self.settings[server.id].get('rid', None)
        if rid is not None:
            role = [r for r in server.roles if r.id == rid][0]
            if self.settings[server.id].get('strictrole', True):
                return role in author.roles
            else:
                return author.top_role >= role
        return True

    def _is_ignored(self, author: Union[discord.Member, discord.Role]):
        ignored = self.settings[author.server.id].get('ignored', [])
        if author.id in ignored:
            return True
        if isinstance(author, discord.Member):
            for role in author.roles:
                if self._is_ignored(role):
                    return True
        return False

    def _is_valid_interval(self, seconds: int, server: discord.Server=None):
        min_t = 1800
        max_t = 604800
        if server is not None:
            min_t = self.settings[server.id].get('min_time', 1800)
            max_t = self.settings[server.id].get('max_time', 604800)
        return min_t <= seconds <= max_t

    def _at_channel_limit(self, author: discord.Member):
        server = author.server
        if server.id in self.channels:
            if len(self.channels[server.id]) >= \
                    self.settings[server.id]['schan_limit']:
                return False
            count = 0
            for k, v in self.channels[server.id].items():
                if v['owner'] == author.id:
                    count += 1
                if count >= self.settings[server.id]['uchan_limit']:
                    return False
        return True

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
