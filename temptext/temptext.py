import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
import logging
import os
import asyncio
from datetime import datetime, timedelta
assert asyncio  # shakes fist at linter


log = logging.getLogger("red.TempText")

creationmessage = "Hi {0.mention}, I've created your channel here. " \
                  "People eligible to join can do so by using the following " \
                  "command.\n`{1}jointxt {2.id}`"  # author, prefix, channel


class TmpTxtError(Exception):
    pass


class TempText:

    __author__ = "mikeshardmind"
    __version__ = "1.0a"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/temptext/settings.json')
        self.channels = dataIO.load_json('data/temptext/channels.json')
        self.everyone_perms = discord.PermissionOverwrite(read_messages=False)
        self.joined_perms = discord.PermissionOverwrite(read_messages=True,
                                                        send_messages=True)
        self.owner_perms = discord.PermissionOverwrite(read_messages=True,
                                                       send_messages=True,
                                                       manage_channels=True,
                                                       manage_roles=True)
        self._load()

    def update_settings(self, server: discord.Server, data=None):
        if server.id not in self.settings:
            self.settings[server.id] = {'active': False,
                                        'rid': None,
                                        'strict': True,
                                        'default_time': 14400,  # 4h in s,
                                        'author_is_owner': False
                                        }
        if data is not None:
            self.settings[server.id].update(data)
        self.save_settings()

    def save_settings(self):
        dataIO.save_json("data/temptext/settings.json", self.settings)

    def save_channels(self):
        dataIO.save_json("data/temptext/channels.json", self.channels)

    def _load(self):
        now = datetime.utcnow()
        channel_ids = [c.id for c in self.bot.get_all_channels()]
        self.channels = {k: v for k, v in self.channels.items()
                         if v['id'] in channel_ids}
        valid_chans = [c for c in self.bot.get_all_channels()
                       if c.id in self.channels.keys()]
        for channel in valid_chans:

            if channel.created_at + \
                timedelta(seconds=self.channels[channel.id]['lifetime']) > \
                    now:
                sec = 0
            else:
                sec = (channel.created_at +
                       timedelta(seconds=self.channels[channel.id]['lifetime'])
                       - nowdelete_in).seconds

            coro = self._temp_deletion(channel.id)
            self.bot.loop.call_later(sec, self.bot.loop.create_task, coro)

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

        N.B. This is specifically the role checking on creating a temp channel,
        not on joining one.
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.update_settings(server)

        strict = not self.settings[server.id]['strict']
        self.update_settings(server, {'strict': strict})
        await self.bot.say("Strict mode: {}".format(strict))

    @tmptxtset.command(name="togglesownership", pass_context=True, no_pm=True)
    async def toggleownership(self, ctx):
        """
        toggles whether someone owns the channels they make
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.update_settings(server)

        ownership = not self.settings[server.id]['author_is_owner']
        self.update_settings(server, {'author_is_owner': ownership})
        await self.bot.say("Author is owner: {}".format(ownership))

    @tmptxtset.command(name="defaulttime", pass_context=True, no_pm=True)
    async def setdefaulttime(self, ctx, **timevalues):
        """
        sets the time used for temp text channels when no time is provided
        time should be between 10 minutes and 2 days
        takes time in mintes(m), hours (h), days (d) in the format
        interval=quantity
        example usage for 1 hour 30 minutes: [p]tmptxtset defaulttime h=1 m=30
        default is 4h
        """

        seconds = self._parse_time(timevalues)
        if not self._is_valid_interval(seconds):
            return await self.bot.say("That wasn't a valid time")

        self.update_settings(ctx.message.server, {'default_time': seconds})
        await self.bot.say("Default set")

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

    @commands.command(pass_context=True, no_pm=True, name="jointxt")
    async def _join_text(self, ctx, chan_id: str):
        """try to join a room"""
        author = ctx.message.author
        try:
            await self.bot.delete_message(ctx.message)
        except Exception:
            pass
        c = discord.utils.get(self.bot.get_all_channels(), id=chan_id,
                              server__id=author.server.id)
        if chan_id not in self.channels or c is None:
            return await self.bot.say("That isn't a joinable channel")
        if not self._is_allowed(author, chan_id):
            return await self.bot.say("Sorry, you can't join that room")

        try:
            await self.bot.edit_channel_permissions(c, author,
                                                    self.joined_perms)
        except discord.Forbidden:
            await self.bot.say("Wait what the... who removed my perms?.. "
                               "this is going to break all the things ")
        except discord.HTTPException:
            await self.bot.say("Huh... discord issue, try again later")
        except Exception as e:
            log.debug("{}".format(e))
            await self.bot.say("Something unexpected went wrong. Good luck.")
        else:
            await self.bot.say("Click this. It's a channel link, "
                               "not a hashtag."
                               "\nIf it isn't clickable, it isn't for you. "
                               "{0.mention}".format(c))

    @commands.cooldown(5, 600, commands.BucketType.user)
    @commands.command(pass_context=True, name="tmptxt", no_pm=True)
    async def _temp_add(self, ctx, name: str, **args):
        """
        Makes a temp channel to be automagically deleted in anywhere between
        10 minutes and 2 days in the future

        Time value is optional, defaulting to whatever your server's default is
        if none is provided
        takes time in mintes(m), hours (h), days (d) in the format
        interval=quantity
        example usage for 1 hour 30 minutes: [p]tmptxtset defaulttime h=1 m=30

        """

        author = ctx.message.author
        if not self._is_allowed(author):
            return

        try:
            x = await self._process_temp(ctx.prefix, author, args, name)
        except TmpTxtError as e:
            await self.bot.say("{}".format(e))
        else:
            await self.bot.say("Channel made -> {0.mention}".format(x))

    async def _process_temp(self, prefix, author: discord.Member, timevalues,
                            channel_name=None, role_id=None):
        server = author.server
        if len(timevalues) == 0:
            seconds = self.settings[server.id]['default_time']
        else:
            seconds = self._parse_time(timevalues)

        if not self._is_valid_interval(seconds):
            raise TmpTxtError("That wasn't a valid time")
            return

        try:
            author_perms = self.owner_perms \
                if self.settings[server.id]['author_is_owner'] \
                else self.joined_perms
            x = await self.bot.create_channel(server, channel_name,
                                              (server.default_role,
                                               self.everyone_perms),
                                              (author, author_perms),
                                              (server.me, self.joined_perms)
                                              )
        except discord.Forbidden:
            raise TmpTxtError("I literally can't even")
            return
        except Exception as e:
            log.debug("{}".format(e))
            raise TmpTxtError("Something unexpected happened. Try again later")
            return

        self.channels[x.id] = {'id': x.id,
                               'rid': role_id,
                               'lifetime': seconds,
                               'owner': author.id,
                               'server': server.id}
        self.save_channels()

        self._scheduling_things_sucks(x.id, seconds)
        await self.bot.send_message(x, creationmessage.format(author, prefix,
                                                              x))
        return x

    def _scheduling_things_sucks(self, chan_id, seconds):
        coro = self._temp_deletion(chan_id)
        self.bot.loop.call_later(seconds, self.bot.loop.create_task, coro)

    async def _temp_deletion(self, *channel_ids: str):

        channels = [c for c in self.bot.get_all_channels()
                    if c.id in channel_ids]

        disappeared = [cid for cid in channel_ids
                       if cid not in [c.id for c in channels]]
        self.channels = \
            {k: v for k, v in self.channels.items()
             if v['id'] not in disappeared}

        for channel in channels:
            try:
                cid = channel.id
                await self.bot.delete_channel(channel)
            except Exception as e:
                log.debug("{}".format(e))
            else:
                self.channels.pop(cid, None)

        self.save_channels()

    def _is_allowed(self, author: discord.Member, chan_id=None):
        server = author.server
        if server.id not in self.settings:
            return False
        if not self.settings[server.id].get('active', False):
            return False
        if chan_id is not None:
            rid = self.channels[chan_id].get('rid', None)
            if rid is not None:
                role = [r for r in server.roles if r.id == rid][0]
                if role not in author.roles:
                    return False
        else:
            rid = self.settings[server.id].get('rid', None)
            if rid is not None:
                role = [r for r in server.roles if r.id == rid][0]
                if self.settings[server.id].get('strict', True):
                    return role in author.roles
                else:
                    return author.top_role >= role
        return True

    def _parse_time(**kwargs):
        return ((kwargs.pop('d', 0) * 24
                 + kwargs.pop('h', 0)) * 60
                + kwargs.pop('m', 0)) * 60

    def _is_valid_interval(self, seconds: int):
        return 600 <= seconds <= 172800  # 10m <= seconds <= 2d


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
    bot.add_cog(n)
