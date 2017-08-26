import os
import discord
import asyncio
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks
from cogs.utils.chat_formatting import box, pagify


class InJokes:
    """
    This cog has hard coded values to ensure it will not work for you without
    making changes. Because this is meant to do some very specific things
    that nobody else should need or even want
    """

    __author__ = "mikeshardmind"
    __version__ = "0.1a"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/injokes/settings.json')
        self.is_valid = False
        self.sids = ["78634202018357248", "322594330541948928"]
        self.checked = False
        self.currencies = {"$": ("dollars", 20),
                           "€": ("euros", 20),
                           "£": ("pounds", 20),
                           "¥": ("yen", 2200),
                           "₽": ("rubles", 1200)
                           }

    def save_json(self):
        dataIO.save_json("data/injokes/settings.json", self.settings)

    @checks.is_owner()
    @commands.command(name="canadian", pass_context=True)
    async def set_canadian(self, ctx, user: discord.Member):
        if user.id not in self.settings['canadians']:
            self.settings['canadians'].append(user.id)
            self.save_json()

    @checks.is_owner()
    @commands.command(name="notcanadian", pass_context=True)
    async def set_canadian(self, ctx, user: discord.Member):
        if user.id in self.settings['canadians']:
            self.settings['canadians'].remove(user.id)
            self.save_json()

    async def self_validate(self):
        self.checked = True
        if 'canadians' not in self.settings:
            self.settings['canadians'] = []
        if self.bot.user.id == "275047522026913793":
            self.is_valid = True

    async def do_the_thing(self, message):
        channel = message.channel
        author = message.author
        server = message.server
        if not self.checked:
            await self.self_validate()
        if not self.is_valid:
            return
        if server.id not in self.sids:
            return

        content = message.clean_content
        currency = content[:1]
        if currency not in self.currencies:
            return
        d = self.currencies[currency]

        if int(content[1:]) != 20 and int(content[1:]) != d[1]:
            return

        if d[1] == int(content[1:]):
            output = "Yeah, I'd blow you for {} {}. ".format(d[1], d[0])
            if author.id in self.settings["canadian"] and currency == "$":
                output += "Real dollars, not canadian monopoly money."
        else:
            output = "You must think I'm stupid or something. "
            output += "I'm taking your {} {} ".format(content[1:], d[0])
            output += "for wasting my time. Come back with "
            output += "{} {} and ".format(d[1], d[0])
            output += "I might fake enough interest to get you off"

        await self.bot.send_message(channel, output)


def check_folder():
    f = 'data/injokes'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/injokes/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = InJokes(bot)
    bot.add_listener(n.do_the_thing, "on_message")
    bot.add_cog(n)
