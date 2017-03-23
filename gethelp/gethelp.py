import os
import sys
import asyncio
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks

log = logging.getLogger('red.GetHelp')

class GetHelp:
    """Custom cog for storing a callable embed"""

    __author__ = "mikeshardmind"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/gethelp/settings.json')


    def save_json(self):
        dataIO.save_json("data/gethelp/settings.json", self.settings)




    @checks.is_owner()
    @commands.group(name="helpset", pass_context=True)
    async def helpset(self, ctx):
        """settings management for Resourcer"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @helpset.command(name="title", pass_context=True)
    async def helpset_title(self, ctx):
        """Interactive title set"""

        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            await self.bot.say("Please give me the title")
            message = await self.bot.wait_for_message(channel=channel, author=author)
            title = message.clean_content
            self.settings['title'] = title
            self.save_json()
        else:
            await self.bot.say("You can't use that here.")


    @checks.is_owner()
    @helpset.command(name="footer", pass_context=True)
    async def helpset_footer(self, ctx):
        """interactive footer setter"""

        author = ctx.message.author
        channel = ctx.message.channel

        if channel.is_private:
            await self.bot.say("Please give me the footer")
            message = await self.bot.wait_for_message(channel=channel, author=author)
            footer = message.clean_content
            if footer == "timestamp":
                if self.settings['timestamp']:
                    footer = 'last updated: {}'.format(self.settings['timestamp'])
                    self.settings['footer'] = footer
                    self.save_json()
            else:
                self.settings['footer'] = footer
                self.save_json()
        else:
            await self.bot.say("You can't use that here.")

    @checks.is_owner()
    @helpset.command(name="msg", pass_context=True)
    async def helpset_msg(self, ctx):
        """interactive message set"""

        author = ctx.message.author
        channel = ctx.message.channel


        if channel.is_private:
            await self.bot.say("Please give me the message to be embedded.")
            message = await self.bot.wait_for_message(channel=channel, author=author)
            content = message.clean_content
            timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
            self.settings['content'] = content
            self.settings['timestamp'] = timestamp
            self.save_json()
        else:
            await self.bot.say("You can't use that here")


    @commands.command(name="gethelp", pass_context=True)
    async def gethelp(self, ctx):
        """get help"""

        who = ctx.message.author

        content = self.settings['content']
        timestamp = self.settings['timestamp']
        footer = self.settings['footer']
        title = self.settings['title']
        if content and timestamp and footer and title:
            em = discord.Embed(description=content, color=discord.Color.purple())
            em.set_author(name=title)
            em.set_footer(text=footer)

            await self.bot.send_message(who, embed=em)

    @checks.is_owner()
    @commands.command(name="puthelp", pass_context=True, hidden=True)
    async def puthelp(self, ctx):
        """put help here"""

        message = ctx.message
        where = message.channel

        content = self.settings['content']
        timestamp = self.settings['timestamp']
        footer = self.settings['footer']
        title = self.settings['title']
        if content and timestamp and footer and title:
            em = discord.Embed(description=content, color=discord.Color.purple())
            em.set_author(name=title)
            em.set_footer(text=footer)

            await self.bot.send_message(where, embed=em)

        try:
            await self.bot.delete_message(message)
        except Exception as e:
            log.debug("{}".format(e))





def check_folder():
    f = 'data/gethelp'
    if not os.path.exists(f):
        os.makedirs(f)

def check_file():
    f = 'data/gethelp/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    n = GetHelp(bot)
    bot.add_cog(n)
