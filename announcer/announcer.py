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
    __version__ = "3.0.1"
    __author__ = "mikeshardmind (Sinbad#0001)"

    def __init__(self, bot):
        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}
        # this shouldn't be possible, but I've gotten multiple reports
        # of it happening so...
        if self.settings.get('optout', []) is None:
            self.settings['optout'] = []

    def save_settings(self):
        dataIO.save_json(path + '/settings.json', self.settings)

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
                elif channel.permissions_for(server.me).send_messages:
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
            output += "\n\nSuccessful:"
            for i in cases['successes']:
                output += "\n{0.server.name} | {0.name}".format(i)
        if len(cases['permissions']) > 0:
            output += "\n\nI lack permissions to send to these locations:\n" \
                "Guild | Channel"
            for i in cases['permissions']:
                output += "\n{0.server.name} | {0.name}".format(i)
        if len(cases['exceptions']) > 0:
            output += "\n\nI ran into unknown issues while trying " \
                "to send to the following\nGuild | Channel"
            for i in cases['exceptions']:
                output += "\n{0.server.name} | {0.name}".format(i)
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
            await self.bot.say(page)

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
            return await self.bot.say(
                "Ignoring Request: Invalid place to send announcements"
            )

        server = channel.server
        member = server.get_member(ctx.message.author.id)

        if member is None:
            return await self.bot.say(
                "Ignoring request: You don't have permission to make "
                "announcements for this server (requires manage server)"
            )

        if not member.server_permissions.manage_server:
            return await self.bot.say(
                "Ignoring request: You don't have permission to make "
                "announcements for this server (requires manage server)"
            )

        if channel.permissions_for(server.me).send_messages is False:
            await self.bot.say(
                "Warning: I cannot speak in that channel I "
                "will add it to the list, but announcements"
                " will not be sent if this is not fixed"
            )

        if server.id not in self.settings:
            self.settings[server.id] = {'channel': channel.id}
        else:
            self.settings[server.id]['channel'] = channel.id
        self.save_settings()
        await self.bot.say(
            "Announcement channel for the associated server has been set"
        )

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

        for server in self.bot.servers:
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
    @announcerset.command(name='begincleanup', pass_context=True)
    async def cleanup_entries(self, ctx):
        """
        cleans up bad entries in settings
        """
        self.info = {
            'no_chan': [],
            'invalid_chan': [],
            'lacking_perms': []
        }

        for server in self.bot.servers:
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

        no_srv = [
            i for i in self.settings.keys() if i not in [
                s.id for s in self.bot.servers
            ]
        ]
        self.settings = {
            k: v for k, v in self.settings.items()
            if k not in no_srv
        }
        self.save_settings()
        output = 'I removed entries for servers I am not in.'
        if any(len(v) > 0 for k, v in self.info.items()):
            output += (
                '\nI have also gathered '
                'information about misconfigured channels. '
                'If you would like to send '
                'an automtically generated message to those '
                'server owners about fixing this, use '
                '`{0.prefix}announcerset messageforfix`.'
                '\nIf you would instead like to remove '
                'those entries from settings, '
                'use `{0.prefix}announcerset cleansettings`'
            ).format(ctx)
        else:
            output += '\nI did not find any other issues.'

        await self.bot.say(output)

    @checks.is_owner()
    @announcerset.command(name='cleansettings', pass_context=True)
    async def cleanupsettings(self, ctx):
        """
        removes all bad entries
        """

        if not hasattr(self, 'info'):
            return await self.bot.say(
                "Use `{0.prefix}announcerset begincleanup` first".format(ctx)
            )

        bad_server_ids = [
            s.id for s in list(
                self.info['no_chan']
                + self.info['lacking_perms']
                + self.info['invalid_chan']
            )
        ]
        if len(bad_server_ids) == 0:
            return await self.bot.say(
                'Are you sure there are any bad entries?'
                '\nYou can use `{}getinfo` to be certain.'
            )

        self.settings = {
            k: v for k, v in self.settings.items()
            if k not in bad_server_ids
        }
        self.save_settings()
        await self.bot.say('Invalid entries ahvae been removed')

    @checks.is_owner()
    @announcerset.command(name='messageforfix', pass_context=True)
    async def messageforconfigure(self, ctx):
        """
        message each server owner about configuring announcements
        """

        if not hasattr(self, 'info'):
            return await self.bot.say(
                "Use `{}announcerset getinfo` first".format(ctx.prefix)
            )

        relevant_servers = [srv for srv in self.bot.servers
                            if srv in list(self.info['invalid_chan']
                                           + self.info['no_chan']
                                           + self.info['lacking_perms'])
                            and srv.id not in self.settings.get('optout', [])]

        who = set(s.owner.id for s in relevant_servers)

        for w in who:
            if self.settings.get('optout', []) is None:
                # This really shouldn't be possible
                # Yet, reports of it have happened.
                self.settings['optout'] = []
            if w in self.settings.get('optout', []):
                continue
            send = ("Hey, This is a message issued by my owner to inform "
                    "you that you aren't recieving "
                    "announcements about the bot in one or more of your "
                    "servers. If this is intentional, feel free to ignore "
                    "this message, otherwise, you can use "
                    "`announcerset addchan` "
                    "in a channel you would like the announcements in for the "
                    "servers.\n"
                    "You can opt out of future notifications about this"
                    "by using `announcerset optout`. Alternatively, "
                    "you can opt out of notifications about this for a "
                    "specific server by using `announcerset srvoptout` "
                    "from that server."
                    "\nIssue details:"
                    "\nServer Name: Issue\n")

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
            try:
                await self.bot.send_message(where, send)
            except discord.Forbidden:
                await self.bot.say((
                    "{0.mention} isn't accepting DMs"
                    "\nI'm opting them out of future "
                    "messages about this.").format(where)
                )
                self.settings['optout'] = \
                    (self.settings.get('optout', [])).append(w)
                self.save_settings()

    @checks.serverowner()
    @announcerset.command(name='srvoptout', pass_context=True, no_pm=True)
    async def srvoptout(self, ctx):
        """
        opt out of notifications about bot announcements
        not being configured properly for the current server
        """
        _id = ctx.message.server.id
        self.settings['optout'] = self.settings.get('optout', [])
        if _id in self.settings:
            return await self.bot.say(
                "You already opted out for this server. "
                "You can opt back in with "
                "{}announcerset srvoptin".format(ctx.prefix)
            )
        self.settings['optout'].append(_id)
        await self.bot.say(
            "Okay, you won't be informed about misconfigured "
            "announcement channels on this server. "
            "If you cange your mind, you can opt back in with "
            "`{}announcerset srvoptin`".format(ctx.prefix)
        )
        self.save_settings()

    @checks.serverowner()
    @announcerset.command(name='srvoptin', pass_context=True, no_pm=True)
    async def srvoptin(self, ctx):
        """
        opt into notifications about bot announcements
        not being configured properly for the current server
        """
        _id = ctx.message.server.id
        self.settings['optout'] = self.settings.get('optout', [])
        if _id not in self.settings['optout']:
            return await self.bot.say(
                    "You aren't opted out."
                )
        self.settings['optout'].remove(_id)
        await self.bot.say(
            "You will recieve notifications about announcement "
            "channels on this server again"
        )
        self.save_settings()

    @announcerset.command(name="optout", pass_context=True)
    async def optout(self, ctx):
        """
        opt out of recieving notifications about
        servers that are not configured for announcements
        """
        _id = ctx.message.author.id
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
        _id = ctx.message.author.id
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

    @checks.serverowner_or_permissions(manage_server=True)
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
