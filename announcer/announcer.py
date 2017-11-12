import os
import asyncio  # noqa: F401
import discord  # noqa: F401
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from .utils.chat_formatting import pagify


class Announcer:
    """Configureable Announcements."""
    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/announcer/settings.json')

    def save_settings(self):
        dataIO.save_json('data/announcer/settings.json', self.settings)

    @checks.is_owner()
    @commands.command(name="announcer", pass_context=True)
    async def announcer(self, ctx, *, msg):
        """Announces a message to all channels configured."""

        server_ids = map(lambda s: s.id, self.bot.servers)
        cases = {'exceptions': [],
                 'permissions': [],
                 'not_found': [],
                 'not_server': [],
                 'successes': []}
        for server_id in server_ids:
            if server_id in self.settings:
                server = self.bot.get_server(server_id)
                channel = server.get_channel(
                          self.settings[server_id]['channel'])
                if channel is None:
                    cases['not_found'].append(server)
                if channel.permissions_for(server.me).send_messages:
                    try:
                        await self.bot.send_message(channel, msg)
                    except Exception:
                        cases['exceptions'].append(channel)
                    else:
                        cases['successes'].append(channel)
                else:
                    cases['permissions'].append(channel)

        for k, v in self.settings.items():
            if k not in server_ids:
                cases['not_server'].append(k)

        output = "Succesfully sent announcements to {} of {} locations".format(
            len(cases['successes']), len(self.settings))
        if len(cases['successes']) > 0:
            output += "\n\nSuccessful: \n"
            for i in cases['successes']:
                output += "{} ".format(i.mention)
        if len(cases['permissions']) > 0:
            output += "\n\nI lack permissions to send to these locations: \n"
            for i in cases['permissions']:
                output += "{} ".format(i.mention)
        if len(cases['exceptions']) > 0:
            output += "\n\nI ran into unknown issues while trying " \
                "to send to the following channels \n"
            for i in cases['exceptions']:
                output += "{} ".format(i.mention)
        if len(cases['not_found']) > 0:
            output += "\n\nThe following servers have entries for " \
                "channels that no longer exist"
            for i in cases['not_found']:
                output += "\n{} ".format(i.name)
        if len(cases['not_server']) > 0:
            output += "\n\nI have a few server IDs that I can't " \
                "seem to find in my active servers:"
            for i in cases['not_server']:
                output += "{} ".format(i)

        for page in pagify(output):
            await self.bot.whisper(page)

    @checks.is_owner()
    @commands.group(name="announcerset", pass_context=True)
    async def announcerset(self, ctx):
        """Settings for announcer"""

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @announcerset.command(name="addchan", pass_context=True)
    async def addchan(self, ctx, *, channel_id=None):
        """adds a channel to the announcer's channel list
        defaults to the current channel, can optionally be given
        a channel id
        Will not announce to Direct Message"""

        channel = None
        server = None
        if channel_id is None:
            channel = ctx.message.channel
            server = ctx.message.server
        else:
            for serv in self.bot.servers:
                for chan in serv.channels:
                    if chan.id == channel_id:
                        channel = chan
                        server = serv

        if channel is None:
            await self.bot.say("I cannot find that channel")
        elif channel.is_private:
            await self.bot.say("Ignoring Request: "
                               "Invalid place to send announcements")
        else:
            if channel.permissions_for(server.me).send_messages is False:
                await self.bot.say("Warning: I cannot speak in that channel I "
                                   "will add it to the list, but announcements"
                                   " will not be sent if this is not fixed")

            if server.id not in self.settings:
                self.settings[server.id] = {'channel': channel.id}
            else:
                self.settings[server.id]['channel'] = channel.id
            self.save_settings()
            await self.bot.say("Announcement channel for the associated"
                               "server has been set")

    @checks.is_owner()
    @announcerset.command(name="delchan", pass_context=True)
    async def delchan(self, ctx, *, channel_id=None):
        """removes a channel from the announcements list
        defaults to current if not given a channel id"""

        channel = None
        server = None
        if channel_id is None:
            channel = ctx.message.channel
            server = ctx.message.server
        else:
            for serv in self.bot.servers:
                for chan in serv.channels:
                    if chan.id == channel_id:
                        channel = chan
                        server = serv

        if server.id in self.settings:
            if channel.id == self.settings[server.id]['channel']:
                self.settings[server.id]['channel'] = None
                await self.bot.say("Channel removed from announcment list")
                self.save_settings()
            else:
                await self.bot.say("This is not an announcement channel")
                output = self.settings[server.id]['channel']
                await self.bot.say("Hint: The announcement channel for the "
                                   "server is <#{}>".format(output))
        else:
            await self.bot.say("This channel is not an announcement channel")


def check_folder():
    f = 'data/announcer'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/announcer/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = Announcer(bot)
    bot.add_cog(n)
