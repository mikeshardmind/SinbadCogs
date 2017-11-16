import pathlib
import asyncio
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks

path = 'data/multiquote'


class MultiQuote:
    """
    Multiquote Activate
    """

    __author__ = "mikeshardmind (Sinbad#0413)"
    __version__ = "2.0.0"

    def __init__(self, bot):

        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}
        if "global" not in self.settings:
            self.settings["global"] = {'csmq': False}

    def save_json(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    @commands.group(name="multiquoteset", pass_context=True, no_pm=True)
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
    @multiquoteset.command(name="csmqtoggle")
    async def _csmq_setting(self):
        """
        Enables cross server multiquotes
        This has serious performance scaling issues
        Do not enable this on a public bot.
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

    @checks.is_owner()
    @commands.command(
        pass_context=True, name='rangequote', aliases=["rmq"], hidden=True)
    async def _rmq(self, ctx, first: str, last: str):
        """quotes a range (inclusive)"""
        a = await self.get_msg(first)
        b = await self.get_msg(last)
        if a is None or b is None or a.channel.id != b.channel.id:
            return await self.bot.say("Dumbass messed something up")
        auth = ctx.message.author
        chan = ctx.message.channel
        await self.sendifallowed(auth, chan, a)
        channel = a.channel
        async for m in \
                self.bot.logs_from(channel, limit=1000000,
                                   after=a, before=b, reverse=True):
            await self.sendifallowed(auth, chan, m)
            await asyncio.sleep(1)
        await self.sendifallowed(auth, chan, b)

    @commands.command(
        pass_context=True, name='crossmultiquote', aliases=["csmq", "csq"])
    async def _csmq(self, ctx, *args):
        """
        Multiple Quotes by ID This version is slower the more servers it needs
        to search. I reccomend not enabling this on public bots.
        It is disabled by default
        """

        if self.settings["global"]["csmq"]:
            for message_id in args:
                message = await self.get_msg(str(message_id))
                if message is not None:
                    await self.sendifallowed(ctx.message.author,
                                             ctx.message.channel, message)
                else:
                    em = discord.Embed(description="I\'m sorry, I couldn\'t "
                                                   "find that message",
                                       color=discord.Color.red())
                    await self.bot.send_message(ctx.message.channel, embed=em)

    @commands.command(
        pass_context=True, name='multiquote', aliases=["mq", "ccq"])
    async def _mq(self, ctx, *args):
        """
        Multiple Quotes by message ID (same server only)
        """
        server = ctx.message.channel.server
        if server.id not in self.settings:
            await self.init_settings(server)
        for message_id in args:
            message = await self.get_msg(message_id, server)
            await asyncio.sleep(1)
            if message is not None:
                await self.sendifallowed(ctx.message.author,
                                         ctx.message.channel, message)
            else:
                em = discord.Embed(description='I\'m sorry, I couldn\'t find '
                                   'that message', color=discord.Color.red())
                await self.bot.send_message(ctx.message.channel, embed=em)

    async def get_msg(self, message_id: str, server=None):
        if server is not None:
            for channel in server.channels:
                try:
                    msg = await self.bot.get_message(channel, message_id)
                    if msg:
                        return msg
                except Exception:
                    pass
            return None

        for server in self.bot.servers:
            for channel in server.channels:
                try:
                    msg = await self.bot.get_message(channel,  message_id)
                    if msg:
                        return msg
                except Exception:
                    pass
        return None

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
                em = self.qform(message)
            else:
                em = discord.Embed(description='You don\'t have '
                                   'permission to quote from that server')
        else:
            em = discord.Embed(description='I\'m sorry, I couldn\'t '
                               'find that message', color=discord.Color.red())
        await self.bot.send_message(where, embed=em)

    def qform(self, message):
        channel = message.channel
        server = channel.server
        content = message.content
        author = message.author
        sname = server.name
        cname = channel.name
        avatar = author.avatar_url if author.avatar \
            else author.default_avatar_url
        footer = 'Said in {} #{}'.format(sname, cname)
        em = discord.Embed(description=content, color=author.color,
                           timestamp=message.timestamp)
        em.set_author(name='{}'.format(author.name), icon_url=avatar)
        em.set_footer(text=footer)
        if message.attachments:
            a = message.attachments[0]
            fname = a['filename']
            url = a['url']
            if fname.split('.')[-1] in ['png', 'jpg', 'gif', 'jpeg']:
                em.set_image(url=url)
            else:
                em.add_field(name='Message has an attachment',
                             value='[{}]({})'.format(fname, url),
                             inline=True)
        return em


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = MultiQuote(bot)
    bot.add_listener(n.init_settings, "on_server_join")
    bot.add_cog(n)
