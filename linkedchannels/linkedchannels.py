import os
import asyncio  # noqa: F401
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


class LinkedChannels:
    """links 2 or more channels across discords that the bot can see.
    heavily influenced by Twentysix26's Rift
    https://github.com/Twentysix26/26-Cogs/blob/master/rift/rift.py
    This version is persistent until closed and shows
    who said what on both sides"""

    __author__ = "mikeshardmind"
    __version__ = "1.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/linkedchannels/settings.json')
        self.links = []
        self.initialized = False

    def save_json(self):
        dataIO.save_json("data/linkedchannels/settings.json", self.settings)

    @checks.is_owner()
    @commands.command(name="makelink", pass_context=True)
    async def makelink(self, ctx, name: str, *chan_ids):
        """links two or more channels by id and names the link"""
        if name in self.settings:
            return await self.bot.say("there is an existing link of that name")
        chans = []
        for chan in chan_ids:
            if chan not in chans:
                chans.append(chan)
        if len(chans) > 1:
            self.settings['name'] = {'chans' = chans
                                     'active': False
                                     }

            self.save_json()
            await self.bot.say("Link formed; be sure to activate it")
        else:
            await self.bot.say("I did not get two or more unique channel IDs")

    @checks.is_owner()
    @commands.command(name="unlink", pass_context=True)
    async def unlink(self, ctx, name: str):
        """unlinks two channels by link name"""

        if name in self.links:
            self.links = [l for l in self.links if l['name'] != name]
        self.settings = [l for l in self.settings if l['name'] != name]
        self.save_json()
        await self.bot.say("If there was a link by that name, it has been "
                           "removed.")

    @checks.is_owner()
    @commands.command(name="listlinks", pass_context=True)
    async def list_links(self, ctx):
        """lists the channel links by name"""

        names = [link['name'] for link in self.settings]
        self.bot.say("{}".format(names))

    @checks.is_owner()
    @commands.command(name="togglelink", pass_context=True)
    async def togglelink(self, ctx, name: str):
        """toggles the link status"""
        if name not in self.settings:
            return await self.bot.say("No link by that name")
        self.settings[name]['active'] = not self.settings[name'active]
        self.validate()
        if self.links[name]['active']:
            await self.bot.say("Link activated")
        else:
            await self.bot.say("Link deactivated")

    async def validate(self, name=None):
        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]

        for l in self.settings:
            link = {'name': self.settings[l]['name'],
                    'chans': [],
                    'active': self.settings[l]['active']
                    }
            for channel in channels:
                if self.settings[name]['A'] == channel.id:
                    link['chans'].append(channel)
                if self.settings[name]['B'] == channel.id:
                    link['chans'].append(channel)

            if len(link[chans]) >= 2:
                if self.settings[name]['active']:
                    self.links.append(link)

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
            if channel in link['chans']:
                destinations = [c for c in link['chans'] if c != channel]

        if destinations is not None:
            for d in destinations:
                await self.sender(d, message)

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
            em.set_author(name='{} ({})'.format(author.name, author.id),
                          icon_url=avatar)
            em.set_footer(text=footer)
            await self.bot.send_message(where, embed=em)


def check_folder():
    f = 'data/linkedchannels'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/linkedchannels/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = LinkedChannels(bot)
    bot.add_cog(n)
