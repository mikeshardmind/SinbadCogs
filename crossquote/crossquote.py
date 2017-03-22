import os
import sys
import asyncio
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks

log = logging.getLogger('red.CrossQuote')

class CrossQuote:
    """
    Cross server quote by message ID. Formatting of the embed was taken from
    https://github.com/PaddoInWonderland/PaddoCogs/quote/quote.py
    For the sake of privacy, allowing a quote from another server will require
    that the user attempting to quote from that server can manage messages or
    that someone who can manage server has disabled this check for their server.
    """ #Yes, I am aware you can still copy/paste manually if you can see the ID

    def __init__(self, bot):
        self.bot = bot

        __version__ = "0.1"
        self.bot = bot
        self.settings = dataIO.load_json('data/crossquote/settings.json')


    def save_json(self):
        dataIO.save_json("data/crossquote/settings.json", self.settings)

    @commands.group(name="crossquoteset", pass_context=True, no_pm=True)
    async def crossquoteset(self, ctx):
        """configuration settings for cross server quotes"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.admin_or_permissions(Manage_server=True)
    @crossquoteset.command(name="bypass", pass_context=True, no_pm=True)
    async def allow_without_permission(self, ctx, bypass=None):
        """allows people with manage server to allow users bypass needing
        manage messages to quote from their server to others
        bypass should be True or False. The default value is False"""

        server = ctx.message.server

        if bypass is None:
            await self.bot.say("I was expecting a True or False after that.")
        elif bypass is True:
            if server.id not in self.settings:
                self.init_settings(server)
            self.settings[server.id]['bypass'] = True
            self.save_json()
            await self.bot.say("Now anyone can quote from this server "
                               "if they can see the message")
        elif bypass is False:
            if server.id not in self.settings:
                self.init_settings(server)
            else:
                self.settings[server.id]['bypass'] = False
                self.save_json()
            await self.bot.say("Quoting from this server again requires manage"
                               " messages")
        else:
            await self.bot.say("That doesn't look like valid input!")

    @checks.is_owner()
    @crossquoteset.command(name="init", hidden=True)
    async def manual_init_settings(self):
        """adds default settings for all servers the bot is in
        can be called manually by the bot owner (hidden)"""

        serv_ids = map(lambda s: s.id, self.bot.servers)
        for serv_id in serv_ids:
            if serv_id not in self.settings:
                self.settings[serv_id] = {'bypass': False,
                                          'whitelisted': [], #future feature
                                          'blacklisted': []  #future feature
                                         }
                self.save_json()

    async def init_settings(self, server=None):
        """adds default settings for all servers the bot is in
        when needed and on join"""

        if server:
            if server.id not in self.settings:
                self.settings[server.id] = {'bypass': False,
                                            'whitelisted': [], #future feature
                                            'blacklisted': []  #future feature
                                           }
                self.save_json()
        else:
            serv_ids = map(lambda s: s.id, self.bot.servers)
            for serv_id in serv_ids:
                if serv_id not in self.settings:
                    self.settings[serv_id] = {'bypass': False,
                                              'whitelisted': [], #future feature
                                              'blacklisted': []  #future feature
                                             }
                    self.save_json()



    @commands.command(pass_context=True, name='crossquote')
    async def _q(self, ctx, message_id: int):
        """
        Quote someone with the message id. To get the message id you need to enable developer mode.
        """
        found = False
        for server in self.bot.servers:
            for channel in server.channels:
                if not found:
                    try:
                        message = await self.bot.get_message(channel, str(message_id))
                        if message:
                            found = True
                    except Exception as error:
                        log.debug(error)
        await self.sendifallowed(ctx.message.author, ctx.message.channel, message)


    async def sendifallowed(self, who, where, message=None):
        "checks if a response should be sent, then sends the appropriate response"

        if message:
            channel = message.channel
            server = channel.server
            self.init_settings(server)
            perms_managechannel = channel.permissions_for(who).manage_messages
            can_bypass = self.settings[server.id]['bypass']
            if perms_managechannel or can_bypass:
                content = '\a\n'+message.clean_content
                author = message.author
                timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                avatar = author.avatar_url if author.avatar else author.default_avatar_url
                em = discord.Embed(description=content, color=discord.Color.purple())
                em.set_author(name='Quote from: {} on {}'.format(author.name, timestamp), icon_url=avatar)
            else:
                em = discord.Embed(description='You don\'t have permission to quote from that server')
        else:
            em = discord.Embed(description='I\'m sorry, I couldn\'t find that message', color=discord.Color.red())
        await self.bot.send_message(where, embed=em)



def check_folder():
    f = 'data/crossquote'
    if not os.path.exists(f):
        os.makedirs(f)

def check_file():
    f = 'data/crossquote/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    n = CrossQuote(bot)
    bot.add_listener(n.init_settings, "on_server_join")
    bot.add_cog(n)
