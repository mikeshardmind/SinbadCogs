import os
import asyncio  # noqa: F401
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


class OneWayLink:
    """links 2 channels across discord serversthat the bot can see.
    heavily influenced by Twentysix26's Rift
    https://github.com/Twentysix26/26-Cogs/blob/master/rift/rift.py
    This version is persistent across restarts and unidirectional
    .\n supports multiple active links
    Be Very Very careful when configuring this one,
    I removed some sanity checks
    for personal purposes"""

    __author__ = "mikeshardmind"
    __version__ = "2.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/onewaylink/settings.json')
        self.links = {}
        self.initialized = False
        self.activechans = ['0']

    def save_json(self):
        dataIO.save_json("data/onewaylink/settings.json", self.settings)

    @checks.is_owner()
    @commands.group(name="oneway", pass_context=True)
    async def oneway(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @oneway.command(name="makelink", pass_context=True)
    async def makelink(self, ctx, name: str, inchannel: str, outchannel: str):
        """links two channels by id and names the link"""
        name = name.lower()
        if name in self.settings:
            return await self.bot.say("there is an existing link of that name")

        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]
        channel1 = [c.id for c in channels if c.id == inchannel]
        channel2 = [c.id for c in channels if c.id == outchannel]
        channels = channel1 + channel2

        if len(channels) == 2:
            self.settings[name] = {'chans': channels}
            self.save_json()
            await self.validate()
            if name in self.links:
                await self.bot.say("Link formed.")
        else:
            await self.bot.say("I did not get two or more unique channel IDs")

    @checks.is_owner()
    @oneway.command(name="unlink", pass_context=True)
    async def unlink(self, ctx, name: str):
        """unlinks two channels by link name"""
        name = name.lower()
        if name in self.links:
            chans = self.links[name]
            self.links.pop(name, None)
            self.settings.pop(name, None)
            self.save_json()
            await self.bot.say("Link removed")
        else:
            await self.bot.say("No such link")

    @checks.is_owner()
    @oneway.command(name="listlinks", pass_context=True)
    async def list_links(self, ctx):
        """lists the channel links by name"""

        links = list(self.settings.keys())
        await self.bot.say("Active link names:\n {}".format(links))

    async def validate(self):
        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]

        for name in self.settings:
            chan_ids = list(*self.settings[name].values())
            chans = [c for c in channels if c.id in chan_ids]
            self.links[name] = chans

    async def on_message(self, message):
        """Do stuff based on settings"""
        if not self.initialized:
            await self.validate()
            self.initialized = True

        if message.author == self.bot.user:
            return

        channel = message.channel
        destination = None
        for link in self.links:
            if channel in self.links[link] and \
                    channel.id == self.settings[link]['chans'][0]:
                destination = [c for c in self.links[link] if c != channel][0]

        if destination is not None:
            await self.sender(destination, message)

    async def sender(self, where, message=None):
        """sends the thing"""

        if message:
            channel = message.channel
            server = channel.server
            content = message.clean_content
            author = message.author
            sname = server.name
            cname = channel.name
            timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
            avatar = author.avatar_url if author.avatar \
                else author.default_avatar_url
            footer = 'Said in {} #{} at {} UTC'.format(sname, cname, timestamp)
            em = discord.Embed(description=content,
                               color=discord.Color.purple())
            em.set_author(name='{}'.format(author.name), icon_url=avatar)
            em.set_footer(text=footer)
            await self.bot.send_message(where, embed=em)


def check_folder():
    f = 'data/onewaylink'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/onewaylink/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = OneWayLink(bot)
    bot.add_cog(n)
