import os
import sys
import asyncio
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks

log = logging.getLogger('red.Embedder')

class Embedder:
    """Custom cog for making, storing, and recalling embeds
    Warning: if users have disabled link previews, they cannot see embeds"""

    __author__ = "mikeshardmind"
    __version__ = "0.1a"

    #this version is alpha af
    #No syntax errors, but no testing
    #repeat: case testing has not been done.


    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/embedder/settings.json')


    def save_json(self):
        dataIO.save_json("data/embedder/settings.json", self.settings)

    @commands.group(name="embed", pass_context=True, no_pm=True)
    async def embed(self, ctx):
        """recallable custom embeds"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.admin_or_permissions(Manage_messages=True)
    @embed.group(name="make", pass_context=True, no_pm=True)
    async def make_embed(self, ctx, em_name=None, time=False):
        """makes and stores an embed optional flag for setting
        the creation time as the footer"""

        author = ctx.message.author
        channel = ctx.message.channel
        server = ctx.message.server

        if em_name:
            await self.bot.say("Please give me the title")
            message = await self.bot.wait_for_message(channel=channel, author=author)
            title = message.clean_content

            await self.bot.say("Please give me the message to be embedded.")
            message = await self.bot.wait_for_message(channel=channel, author=author)
            content = message.clean_content

            if time:
                timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
                footer = 'embed created on {} UTC by {}'.format(timestamp, author.name)
            else:
                await self.bot.say("Please give me the footer to be embedded")
                message = await self.bot.wait_for_message(channel=channel, author=author)
                footer = message.clean_content

            if em_name and title and content and footer:
                if server.id not in self.settings:
                    self.settings[server.id] = {}
                self.settings[server.id][em_name] = {'title': title,
                                                     'content': content,
                                                     'footer': footer,
                                                     'author': author.id
                                                    }
                self.save_json()
                await self.bot.say("Embed named \"{}\" stored.".format(em_name))
        else:
            await self.bot.say("I was expecting an embed name")

    @checks.admin_or_permissions(Manage_messages=True)
    @embed.group(name="rm", pass_context=True, no_pm=True)
    async def rm_embed(self, ctx, em_name=None):
        """removes an embed from storage"""
        server = ctx.message.server

        if em_name:
            if server.id in self.settings:
                key = self.settings[server.id].pop(em_name, None)
                self.save_json()
                if key:
                    await self.bot.say("Embed stored by name: \"{}\" has been removed".format(key))
                else:
                    await self.bot.say("No such embed.")
            else:
                await self.bot.say("I don't have any embeds stored for this server")
        else:
            await self.bot.say("I was expecting the name of the embed to remove")

    @embed.command(name="get", pass_context=True, no_pm=True)
    async def get(self, ctx, em_name=None, pm=False):
        """get an embed"""

        server = ctx.message.server

        if pm:
            where = ctx.message.author
        else:
            where = ctx.message.channel

        if em_name:
            title = self.settings.get(server.id, {}).get(em_name, {}).get('title')
            content = self.settings.get(server.id, {}).get(em_name, {}).get('content')
            footer = self.settings.get(server.id, {}).get(em_name, {}).get('footer')
            if content and footer and title:
                em = discord.Embed(description=content, color=discord.Color.purple())
                em.set_author(name=title)
                em.set_footer(text=footer)
                await self.bot.send_message(where, embed=em)
                try:
                    await self.bot.delete_message(message)
                except Exception as e:
                    log.debug("{}".format(e))
            else:
                await self.bot.say("I couldn't find an embed by that name for this server.")

        else:
            await self.bot.say("I was expecting the name of the embed you wanted.")

    @embed.command(name="list", pass_context=True, no_pm=True)
    async def embed_list(self, ctx):
        """lists embeds"""

        ems = []
        server = ctx.message.server
        if server.id in self.settings:
            for key in self.settings[server.id]:
                ems.append(key)


        if ems:
            em_names = ", ".join(ems)
            await self.bot.say("here are the names of the embeds "
                               "on this server: {}".format(em_names))
        else:
            await self.bot.say("I don't have any embeds stored for this server")




def check_folder():
    f = 'data/embedder'
    if not os.path.exists(f):
        os.makedirs(f)

def check_file():
    f = 'data/embedder/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    n = Embedder(bot)
    bot.add_cog(n)
