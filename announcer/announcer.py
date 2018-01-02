import pathlib
import asyncio  # noqa: F401
import discord  # noqa: F401
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from .utils.chat_formatting import pagify

path = 'data/announcer'


class Announcer:
    """Configureable Announcements."""
    __version__ = "1.2.1"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}

    def save_settings(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    @checks.is_owner()
    @commands.command(name="announcer", pass_context=True)
    async def announcer(self, ctx, *, msg):
        """Announces a message to all channels configured."""

        server_ids = map(lambda s: s.id, self.bot.servers)
        for server_id in server_ids:
            if server_id in self.settings:
                server = self.bot.get_server(server_id)
                channel = server.get_channel(
                          self.settings[server_id]['channel'])
                if channel is None:
                    pass
                elif channel.permissions_for(server.me).send_messages:
                    try:
                        await self.bot.send_message(channel, msg)
                    except Exception:
                        pass

        await self.bot.say('Announcement sent.')

    @checks.is_owner()
    @commands.group(name="announcerset", pass_context=True)
    async def announcerset(self, ctx):
        """Settings for announcer"""

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.serverowner_or_permissions(manage_server=True)
    @announcerset.command(name="addchan", pass_context=True)
    async def addchan(self, ctx, *, channel: discord.Channel=None):
        """adds a channel to the announcer's channel list
        defaults to the current channel, can optionally be given
        a channel
        Will not announce to Direct Message"""

        if channel is None:
            channel = ctx.message.channel

        if channel.is_private:
            return await self.bot.say("Ignoring Request: "
                                      "Invalid place to send announcements")

        server = channel.server
        member = server.get_member(ctx.message.author.id)

        if member is None:
            return await self.bot.say(
                "Ignoring request: You don't have permission to make "
                "announcements for this server (requires manage server)")

        if not member.server_permissions.manage_server:
            return await self.bot.say(
                "Ignoring request: You don't have permission to make "
                "announcements for this server (requires manage server)")

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
    @announcerset.command(name="getinfo", pass_context=True)
    async def getinfo(self, ctx):
        """
        get a list of servers without a channel set,
        with a channel set that is invalid,
        and with a channel set without permissions
        """

        self.info = {
            'no_chan': [],
            'invalid_chan': [],
            'lacking_perms': []
        }

        for server in self.bot.server:
            if server.id in self.settings:
                channel = server.get_channel(
                    self.settings[server.id]['channel']
                )
                if channel is None:
                    self.info['invalid_chan'].append(server)
                elif not channel.permissions_for(
                        server.me).send_messages:
                    self.info['lacking_perms'].append(server)
            else:
                self.info['no_chan'].append(server)

        output = "Servers without a configured channel:"
        for server in self.info['no_chan']:
            output += "\n{0.id} : {0.name}".format(server)
        output += "\nServers with a channel configured that no longer exists:"
        for server in self.info['invalid_chan']:
            output += "\n{0.id} : {0.name}".format(server)
        output += "\nServer where I cannot speak in the configured channel:"
        for server in self.info['lacking_perms']:
            output += "\n{0.id} : {0.name}".format(server)

        for page in pagify(output):
            await self.bot.say(page)

    @checks.is_owner()
    @announcerset.command(name='messageforconfigure', pass_context=True)
    async def messageforconfigure(self, ctx):
        """
        message each server owner about configuring announcements
        """

        if not self.info:
            return await self.bot.say(
                "Use `{}announcerset getinfo` first".format(ctx.prefix)
            )

        relevant_servers = [srv for srv in self.bot.servers
                            if srv in (self.info['invalid_chan']
                                       + self.info['no_chan']
                                       + self.info['lacking_perms'])]

        who = set(s.owner.id for s in relevant_servers)

        for w in who:
            if w in self.settings.get('optout', []):
                continue
            send = ("Hey, just wanted to let you know, you aren't recieving "
                    "announcements about the bot in one or more of your "
                    "servers. If this is intentional, feel free to ignore "
                    "this message, otherwise, you can use "
                    "`announcerset addchan` "
                    "in a channel you would like the announcements in for the "
                    "servers.\n"
                    "You can opt out of future notifications about this"
                    "by using `announcerset optout`"
                    "(Full details below)\nServer Name: Issue\n")

            w_servers = [s for s in relevant_servers if s.owner.id == w]
            w_ic = [s for s in w_servers if s in self.info['invalid_chan']]
            w_nc = [s for s in w_servers if s in self.info['no_chan']]
            w_lp = [s for s in w_servers if s in self.info['lacking_perms']]

            for server in w_servers:
                if server in w_ic:
                    issue = "Announcement channel no longer exists"
                elif server in w_nc:
                    issue = "Announcement channel not set"
                elif server in w_lp:
                    issue = "I can't send messages in the announcement channel"
                send += "{}: {}".format(server.name, issue)

            where = discord.utils.get(self.bot.get_all_members(), id=w)

            await self.bot.send_message(where, send)

    @announcerset.command(name="optout", pass_context=True)
    async def optout(self, ctx):
        """
        opt out of recieving notifications about
        servers that are not configured for announcements
        """
        _id = ctx.author.id
        self.settings['optout'] = self.settings.get('optout', [])
        if _id in self.settings['optout']:
            return await self.bot.say(
                "You already opted out. You can opt in again with "
                "`{}announcerset optin`".format(ctx.prefix)
            )

        self.settings['optout'].append(_id)
        await self.bot.say(
            "Okay, you won't be informed about misconfigured "
            "announcement channels. If you cange your mind, "
            "you can opt back in with `{}announcerset optin`".format(
                ctx.prefix)
        )
        self.save_settings()

    @announcerset.command(name="optin", pass_context=True)
    async def optin(self, ctx):
        """
        opt into recieving notifications about
        servers that are not configured for announcements
        """
        _id = ctx.author.id
        self.settings['optout'] = self.settings.get('optout', [])
        if _id not in self.settings['optout']:
            return await self.bot.say(
                "You aren't opted out."
            )

        self.settings['optout'].remove(_id)
        await self.bot.say(
            "You will recieve notifications about announcement "
            "channels now"
        )
        self.save_settings()

    @checks.is_owner()
    @announcerset.command(name="delchan", pass_context=True)
    async def delchan(self, ctx, *, channel: discord.Channel=None):
        """removes a channel from the announcements list
        defaults to current if not given a channel"""

        if channel is None:
            channel = ctx.message.channel

        if channel.is_private:
            return await self.bot.say(
                "This channel is not an announcement channel")

        server = channel.server
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


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = Announcer(bot)
    bot.add_cog(n)
