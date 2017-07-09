import discord
from .utils import checks
from discord.ext import commands
from cogs.utils.dataIO import dataIO
import os
from datetime import datetime as dt
from random import shuffle


class ChannelDraw:

    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.user = None
        self.locked = False
        self.settings = dataIO.load_json('data/channeldraw/settings.json')

    def save_json(self):
        dataIO.save_json("data/channeldraw/settings.json", self.settings)

    @checks.admin_or_permissions(Manage_channels=True)
    @commands.group(pass_context=True, name='draw', no_pm=True)
    async def draw(self, ctx):
        """Used for the weekly portal draw"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
        if ctx.message.server.id != "108724760782888960":
            return await self.bot.say("This is not ready. "
                                      "Wait for Red v3, or finish it yourself")
        if ctx.message.channel.id != "308106032507256832":
            return await self.bot.say("You can't use that here.")

    @draw.command(pass_context=True, name='bymessages')
    async def by_msgs(self, ctx, first: str, last: str):
        """gets messages of an inclusive range of the message IDs
        in the same channel"""

        a = await self.get_msg(first)
        b = await self.get_msg(last)
        if a is None or b is None:
            return await self.bot.say("I could not find one or both of those")
        if a.channel.id != b.channel.id:
            return await self.bot.say("Those messages are in seperate rooms")
        if self.locked:
            return await self.bot.say("<@{}> has already started the drawing "
                                      .format(self.user.id))
        if a.timestamp >= b.timestamp:
            return await self.bot.send_cmd_help(ctx)

        self.locked = True
        self.user = ctx.message.author
        self.queue.append(a)
        self.mkqueue(a, b, a.channel)
        self.queue.append(b)

        self.settings['latest'] = b.timestamp.strftime("%Y%m%d%H%M")
        self.save_json()
        await self.validate(ctx.message.channel)

    @draw.command(pass_context=True, name='bytimes')
    async def by_times(self, ctx, *, times):
        """gets messages from the channel it was called from between 2 times.\n
        Format should be \nYYYY-MM-DDHH:mm\n
        In chronological order, with a space inbetween them"""

        try:
            t = str(times)
            start, end = t.split(' ')
            start = ''.join(c for c in start if c.isdigit())
            end = ''.join(c for c in end if c.isdigit())
            a = dt.strptime(start, "%Y%m%d%H%M")
            b = dt.strptime(end, "%Y%m%d%H%M")
            pass
        except ValueError:
            return await self.bot.send_cmd_help(ctx)
        if a >= b:
            return await self.bot.send_cmd_help(ctx)

        if self.locked:
            return await self.bot.say("<@{}> has already started the drawing "
                                      .format(self.user.id))

        self.locked = True
        self.user = ctx.message.author

        await self.mkqueue(a, b, ctx.message.channel)
        self.settings['latest'] = b.timestamp.strftime("%Y%m%d%H%M")
        self.save_json()
        await self.validate(ctx.message.channel)

    @draw.command(pass_context=True, name='bytimespan')
    async def by_interval(self, ctx, *, time):
        """gets messages from the channel it was called from
        between now and a time (UTC).\n
        Format should be \n\`YYYY-MM-DDHH:mm\`\n
        """

        try:
            t = str(time)
            t = ''.join(c for c in t if c.isdigit())
            a = dt.strptime(t, "%Y%m%d%H%M")
            b = dt.utcnow()
            pass
        except ValueError:
            return await self.bot.send_cmd_help(ctx)
        if a >= b:
            return await self.bot.send_cmd_help(ctx)

        if self.locked:
            return await self.bot.say("<@{}> has already started the drawing "
                                      .format(self.user.id))

        self.locked = True
        self.user = ctx.message.author
        await self.mkqueue(a, b, ctx.message.channel)
        self.settings['latest'] = b.timestamp.strftime("%Y%m%d%H%M")
        self.save_json()
        await self.validate(ctx.message.channel)

    @draw.command(name="auto", pass_context=True)
    async def autodraw(self, ctx):
        """only works if there is a prior draw on record"""
        if not self.settings['latest']:
            return await self.bot.send_cmd_help(ctx)

        if self.locked:
            return await self.bot.say("<@{}> has already started the drawing "
                                      .format(self.user.id))

        self.locked = True
        self.user = ctx.message.author
        a = dt.strptime(self.settings['latest'], "%Y%m%d%H%M")
        b = ctx.message.timestamp
        await self.mkqueue(a, b, ctx.message.channel)
        await self.validate(ctx.message.channel)
        self.settings['latest'] = b.timestamp.strftime("%Y%m%d%H%M")
        self.save_json()

    async def validate(self, channel):

        shuffle(self.queue)
        while self.locked:
            dm = await self.bot.send_message(self.user,
                                             "Is the following a valid entry?")
            entry = self.queue.pop()
            em = self.qform(entry)
            await self.bot.send_message(self.user, embed=em)
            message = await self.bot.wait_for_message(channel=dm.channel,
                                                      author=self.user)
            reply = message.clean_content.lower()

            if reply[0] == 'y':
                await self.bot.send_message(channel, "{} won the drawing with "
                                            "the following entry"
                                            "".format(entry.author.mention))
                await self.bot.send_message(channel, embed=em)
                self.queue = []
                self.locked = False
            if reply[0] == 'n':
                await self.bot.send_message(self.user, "Ok then...")
                if len(self.queue) == 0:
                    await self.bot.send_message(self.user, "That's all folks")
                    self.locked = False

    async def mkqueue(self, a, b, channel):

        async for message in \
                self.bot.logs_from(channel, limit=1000000,
                                   after=a, before=b, reverse=True):
                self.queue.append(message)

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

    def qform(self, message):
        channel = message.channel
        server = channel.server
        content = message.clean_content
        author = message.author
        sname = server.name
        cname = channel.name
        timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
        avatar = author.avatar_url if author.avatar \
            else author.default_avatar_url
        if message.attachments:
            a = message.attachments[0]
            fname = a['filename']
            url = a['url']
            content += "\nUploaded: [{}]({})".format(fname, url)
        footer = 'Said in {} #{} at {} UTC'.format(sname, cname, timestamp)
        em = discord.Embed(description=content, color=discord.Color.purple())
        em.set_author(name='{}'.format(author.name), icon_url=avatar)
        em.set_footer(text=footer)
        return em


def check_folder():
    f = 'data/channeldraw'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/channeldraw/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = ChannelDraw(bot)
    bot.add_cog(n)
