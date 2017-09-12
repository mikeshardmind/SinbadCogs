import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks
import logging
import asyncio
from threading import Thread
from cogs.utils.chat_formatting import box, pagify
from __main__ import settings
import itertools

log = logging.getLogger('red.BotPermAudit')


class BotPermAudit:
    """
    Tool for auditing permissions the bot has on various servers
    """
    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/botpermaudit/settings.json')
        self.loop = None
        self.output = None
        self.initialize()

    def save_json(self):
        dataIO.save_json('data/botpermaudit/settings.json', self.settings)

    def initialize(self):
        self.loop = asyncio.new_event_loop()
        t = Thread(target=self.start_loop, args=(self.loop,))
        t.start()
        chan_id = self.settings.get('logchannel', None)
        if settings.owner not in self.settings['whitelisted']:
            self.settings['whitelisted'].append(settings.owner)
        if chan_id is not None:
            self.output = self.bot.get_channel(chan_id)
        asyncio.run_coroutine_threadsafe(self.perm_check_loop, self.loop)

    def start_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def perm_check_loop(self):
        while self == self.bot.get_cog("BotPermAudit"):
            for server in self.bot.servers:
                output = "Permissions for: {0.id} || {0.name}".format(server)
                my_perms = server.me.server_permissions
                for p in iter(my_perms):
                    output += "\n{}".format(p)

                if self.output is None:
                    dest = await self.bot.get_user_info(settings.owner)
                else:
                    dest = self.output
                for page in pagify(output, delims=["\n", ","]):
                    try:
                        await self.bot.send_message(dest, box(page))
                    except Exception:
                        log.debug("Failed to send output, appending to log:\n"
                                  "{}".format(page))

            time = self.settings['hours'] * 60 * 60
            asyncio.sleep(time)

    @checks.is_owner()
    @commands.group(name="botauditset", pass_context=True)
    async def botauditset(self, ctx):
        """settings for bot perm audit"""

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @botauditset.command(name="whitelist", pass_context=True, hidden=True)
    async def whitelist(self, ctx, *ids: str):
        """
        whitelist servers or server owners by ID
        """
        self.settings['whitelisted'].extend(ids)
        self.settings['whitelisted'] = unique(self.settings['whitelisted'])
        self.save_json()
        await self.bot.say("k")

    @botauditset.command(name="unwhitelist", pass_context=True, hidden=True)
    async def unwhitelist(self, ctx, *ids: str):
        """
        unwhitelist servers or server owners by ID
        """
        for val in ids:
            if val in self.settings['whitelisted']:
                self.settings['whitelisted'].remove(val)
        self.save_json()
        await self.bot.say("k")

    @botauditset.command(name="autoleavetoggle", pass_context=True,
                         hidden=True)
    async def autoleavetoggle(self, ctx):
        """
        autoleaving is not yet enabled
        will be at some later point.
        """
        return await self.bot.send_cmd_help(ctx)
        self.settings['autoleave'] = not self.settings['autoleave']
        self.save_json()
        if self.settings['autoleave']:
            await self.bot.say("Leaving automagically")
        else:
            await self.bot.say("Only auditing, not leaving")

    @botauditset.command(name="logchannel", pass_context=True)
    async def setlogchan(self, ctx, channel: discord.Channel=None):
        """
        sets the audit log channel use without arguments to switch back to DM
        """
        self.output = channel
        if channel is None:
            self.settings['logchannel'] = None
            await self.bot.say("Audit will be sent via DM")
        else:
            self.settings['logchannel'] = channel.id
            await self.bot.say("Audit info will be posted in "
                               "{0.mention}".format(channel))
        self.save_json()

    @botauditset.command(name="flagperms", pass_context=True, hidden=True)
    async def forbidperms(self, ctx, **perms):
        """
        takes permission settings that are disallowed
        ex. if you dont want the bot being an admin anywhere,
        administrator=True
        ex. if you want to require the bot is able to send messages,
        send_messages=False
        This uses the d.py permission syntax which can be found here
        https://discordpy.readthedocs.io/en/latest/api.html#discord.Permissions
        """
        pass


def unique(a):
    indices = sorted(range(len(a)), key=a.__getitem__)
    indices = set(next(it) for k, it in
                  itertools.groupby(indices, key=a.__getitem__))
    return [x for i, x in enumerate(a) if i in indices]


def check_folder():
    f = 'data/botpermaudit'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/botpermaudit/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {'hours': 24,
                             'logchannel': None,
                             'autoleave': False,
                             'forbiddenperms': {},
                             'whitelisted': []
                             })


def setup(bot):
    check_folder()
    check_file()
    n = BotPermAudit(bot)
    bot.add_cog(n)
