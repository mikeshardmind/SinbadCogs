import discord
from .utils import checks
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from time import time
import os
import datetime
import asyncio  # noqa: F401


class RangeLog:

    __author__ = "mikeshardmind"
    __version__ = "2.0"

    def __init__(self, bot):
        self.bot = bot
        self.file = 'data/rangelog/{}.log'
        self.log = []

    @commands.group(pass_context=True, name='rlog', hidden=True)
    async def rlog(self, ctx):
        """Tools for retrieving arbitrary ranges of messages"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @rlog.command(pass_context=True, name='bymessages',
                  aliases=['bm'], hidden=True)
    async def r_logbm(self, ctx, first: str, last: str):
        """ logs a range of messages bound by message IDs in same channel\n
        Range Inclusive"""

        a = await self.get_msg(first)
        b = await self.get_msg(last)
        if a is None or b is None:
            return await self.bot.say("I could not find one or both of those")
        if a.channel.id != b.channel.id:
            return await self.bot.say("Those messages are in seperate rooms")

        self.log = []
        await self.log_msg(a)
        channel = a.channel
        async for message in \
                self.bot.logs_from(channel, limit=1000000,
                                   after=a, before=b, reverse=True):
            await self.log_msg(message)
        await self.log_msg(b)

        try:
            t = self.file.format(str(time()))
            with open(t, encoding='utf-8', mode="w") as f:
                for message in self.log[::-1]:
                    f.write(message+'\n')
            f.close()
            await self.bot.send_file(ctx.message.channel, t)
            os.remove(t)
        except Exception as e:
            print(e)
        except discord.errors.Forbidden:
            await self.bot.say("I can\'t give you the logs "
                               "if I can\'t upload files.")

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

    async def log_msg(self, message):
        author = message.author
        content = message.clean_content
        timestamp = str(message.timestamp)[:-7]
        to_log = '[{}] {} ({}): {}'.format(timestamp, author.name,
                                           author.id, content)
        self.log.append(to_log)


def check_folder():
    f = 'data/rangelog'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/rangelog/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = RangeLog(bot)
    bot.add_cog(n)
