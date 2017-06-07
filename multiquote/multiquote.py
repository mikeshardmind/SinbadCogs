import os
import sys  # noqa: F401
import asyncio  # noqa: F401
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks

log = logging.getLogger('red.Multiquote')


class MultiQuote:
    """
    Multiquote Activate
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):

        self.bot = bot
        self.settings = dataIO.load_json('data/multiquote/settings.json')
        if "global" not in self.settings:
            self.settings["global"] = {'csmq': False}

    def save_json(self):
        dataIO.save_json("data/multiquote/settings.json", self.settings)

    @commands.group(name="multiquoteset",
                    pass_context=True, no_pm=True)
    async def multiquoteset(self, ctx):
        """configuration settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.admin_or_permissions(Manage_server=True)
    @multiquoteset.command(name="bypasstoggle", pass_context=True, no_pm=True)
    async def allow_without_permission(self, ctx):
        """allows people with manage server to allow users bypass needing
        manage messages to quote from their server to others
        bypass should be True or False. The default value is False"""

        server = ctx.message.server

        if server.id not in self.settings:
            self.init_settings(server)
            self.settings[server.id]['bypass'] = True
            self.save_json()
        else:
            self.settings[server.id]['bypass'] = \
                not self.settings[server.id]['bypass']

        if self.settings[server.id]['bypass']:
            await self.bot.say("Now anyone can quote from this server "
                               "if they can see the message")
        else:
            await self.bot.say("Quoting from this server again requires manage"
                               " messages")

    @checks.is_owner()
    @multiquoteset.command(name="init")
    async def manual_init_settings(self):
        """adds default settings for all servers the bot is in
        can be called manually by the bot owner (hidden)"""

        serv_ids = map(lambda s: s.id, self.bot.servers)
        for serv_id in serv_ids:
            if serv_id not in self.settings:
                self.settings[serv_id] = {'bypass': False,
                                          'whitelisted': [],
                                          'blacklisted': []
                                          }

        self.save_json()

    @checks.is_owner()
    @multiquoteset.command(name="csmqtoggle", hidden=True)
    async def _csmq_setting(self):
        """
        Enables cross server multiquotes
        This has serious performance scaling issues
        Do not enable this on a public bot.
        This feature is hidden for a reason. Use at your own risk
        """
        self.settings["global"]["csmq"] = \
            not self.settings["global"]["csmq"]
        self.save_json()

        if self.settings["global"]["csmq"]:
            await self.bot.say("You were warned. "
                               "if this breaks, turn it back off")
        else:
            await self.bot.say("Probably the best course of action")

    async def init_settings(self, server=None):
        """adds default settings for all servers the bot is in
        when needed and on join"""

        if server:
            if server.id not in self.settings:
                self.settings[server.id] = {'bypass': False,
                                            'whitelisted': [],
                                            'blacklisted': []
                                            }
                self.save_json()
        else:
            serv_ids = map(lambda s: s.id, self.bot.servers)
            for serv_id in serv_ids:
                if serv_id not in self.settings:
                    self.settings[serv_id] = {'bypass': False,
                                              'whitelisted': [],
                                              'blacklisted': []
                                              }
                    self.save_json()

    @commands.command(pass_context=True, name='crossmultiquote',
                      aliases=["csmq"], hidden=True)
    async def _csmq(self, ctx, *args):
        """
        Multiple Quotes by ID This version is slower the more servers it needs
        to search. I reccomend not enabling this on public bots.
        It is disabled by default
        """

        if self.settings["global"]["csmq"]:
            for message_id in args:
                found = False
                for server in self.bot.servers:
                    if server.id not in self.settings:
                        await self.init_settings(server)
                    for channel in server.channels:
                        if not found:
                            try:
                                message = \
                                    await self.bot.get_message(channel,
                                                               str(message_id))
                                if message:
                                    found = True
                            except Exception as error:
                                log.debug("{}".format(error))
                if found:
                    await self.sendifallowed(ctx.message.author,
                                             ctx.message.channel, message)
                else:
                    em = discord.Embed(description="I\'m sorry, I couldn\'t "
                                                   "find that message",
                                       color=discord.Color.red())
                    await self.bot.send_message(ctx.message.channel, embed=em)

    @commands.command(pass_context=True, name='multiquote',
                      aliases=["mq"])
    async def _mq(self, ctx, *args):
        """
        Multiple Quotes by message ID (same server only)
        """
        server = ctx.message.channel.server
        if server.id not in self.settings:
            await self.init_settings(server)
        for message_id in args:
            found = False
            for channel in server.channels:
                if not found:
                    try:
                        message = \
                            await self.bot.get_message(channel,
                                                       str(message_id))
                        if message:
                            found = True
                    except Exception as error:
                        log.debug("{}".format(error))
            if found:
                await self.sendifallowed(ctx.message.author,
                                         ctx.message.channel, message)
            else:
                em = discord.Embed(description='I\'m sorry, I couldn\'t find '
                                   'that message', color=discord.Color.red())
                await self.bot.send_message(ctx.message.channel, embed=em)

    async def sendifallowed(self, who, where, message=None):
        """checks if a response should be sent
        then sends the appropriate response"""

        if message:
            channel = message.channel
            server = channel.server
            self.init_settings(server)
            perms_managechannel = channel.permissions_for(who).manage_messages
            can_bypass = self.settings[server.id]['bypass']
            source_is_dest = where.server.id == server.id
            if perms_managechannel or can_bypass or source_is_dest:
                content = message.clean_content
                author = message.author
                sname = server.name
                cname = channel.name
                timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
                avatar = author.avatar_url if author.avatar \
                    else author.default_avatar_url
                footer = 'Said in {} #{} at {}'.format(sname, cname, timestamp)
                em = discord.Embed(description=content,
                                   color=discord.Color.purple())
                em.set_author(name='{}'.format(author.name), icon_url=avatar)
                em.set_footer(text=footer)
            else:
                em = discord.Embed(description='You don\'t have '
                                   'permission to quote from that server')
        else:
            em = discord.Embed(description='I\'m sorry, I couldn\'t '
                               'find that message', color=discord.Color.red())
        await self.bot.send_message(where, embed=em)


def check_folder():
    f = 'data/multiquote'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/multiquote/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = MultiQuote(bot)
    bot.add_listener(n.init_settings, "on_server_join")
    bot.add_cog(n)
