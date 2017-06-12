import os
import asyncio  # noqa: F401
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


class LinkedChannels:
    """links 2 channels across discords that the bot can see.
    heavily influenced by Twentysix26's Rift
    https://github.com/Twentysix26/26-Cogs/blob/master/rift/rift.py
    This version is persistent until closed and shows
    who said what on both sides"""

    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/linkedchannels/settings.json')
        self.channel1 = None
        self.channel2 = None
        self.active = False
        self.msg1 = False

    def save_json(self):
        dataIO.save_json("data/linkedchannels/settings.json", self.settings)

    @checks.is_owner()
    @commands.command(name="setlink")
    async def makelink(self, chan1, chan2):
        """links two channels by id and names the link"""

        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]
        for c in channels:
            if c.id == chan1:
                self.settings['chan1'] = c.id
            if c.id == chan2:
                self.settings['chan2'] = c.id
        if self.settings['chan1'] is not None and \
                self.settings['chan2'] is not None:
            if await self.validate():
                await self.bot.say("Link formed.")
        else:
            await self.bot.say("Something went wrong. "
                               "It was probably your fault.")
            self.active = False
        self.save_json()

    @checks.is_owner()
    @commands.command(name="togglelink", pass_context=True)
    async def togglelink(self):
        """toggles the link status"""
        self.active = not self.active

        if self.active:
            if await self.validate():
                await self.bot.say("Link activated")
            else:
                self.active = False
                await self.bot.say("Something went wrong. "
                                   "It was probably your fault.")
        else:
            await self.bot.say("Link deactivated")
        self.save_json()

    async def validate(self):
        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]
        checked = 0
        if 'active' not in self.settings:
            self.settings['active'] = False
            self.save_json()
        for c in channels:
            if c.id == self.settings['chan1']:
                self.channel1 = c
                checked += 1
            if c.id == self.settings['chan2']:
                self.channel2 = c
                checked += 1
        if checked == 2:
            self.active = True
            return True
        return False

    async def on_message(self, message):
        """Do stuff based on settings"""
        if not self.msg1:
            await self.validate()
            self.msg1 = not self.msg1

        if message.author == self.bot.user:
            return

        if self.active:
            if message.channel == self.channel1:
                await self.sender(self.channel2, message)
            if message.channel == self.channel2:
                await self.sender(self.channel1, message)

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
            footer = 'Said in {} #{} at {}'.format(sname, cname, timestamp)
            em = discord.Embed(description=content,
                               color=discord.Color.purple())
            em.set_author(name='{} ({})'.format(author.name, author.id), icon_url=avatar)
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
