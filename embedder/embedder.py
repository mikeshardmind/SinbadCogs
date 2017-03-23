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
    #case testing has not been done.


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
    async def make_embed(self, ctx, em_name=None):
        """makes and stores an embed"""

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
            timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')

            await self.bot.say("Should the footer be the creation date? (yes/no)")
            message = await self.bot.wait_for_message(channel=channel, author=author)
            if message.content is "yes":
                footer = 'embed created on {} by {}'.format(timestamp, author.name)
            else:
                await self.bot.say("Okay, what should go here then?")
                message = await self.bot.wait_for_message(channel=channel, author=author)
                footer = message.clean_content

            if em_name and title and content and footer:
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
                await self.bot.say("There are no embeds stored for this server!")
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
            if server.id in self.settings:
                if em_name in self.settings[server.id]:
                    title = self.settings[server.id]['title']
                    content = self.settings[server.id]['content']
                    footer = self.settings[server.id]['footer']
                    if content and timestamp and footer and title:
                        em = discord.Embed(description=content, color=discord.Color.purple())
                        em.set_author(name=title)
                        em.set_footer(text=footer)

                        await self.bot.send_message(where, embed=em)
                        try:
                            await self.bot.delete_message(message)
                        except Exception as e:
                            log.debug("{}".format(e))
                    else:
                        log.debug("Something went terribly "
                                  "wrong when trying to retrieve {} from {}".format(em_name, server.id))
                        await self.bot.say("Something went wrong trying to retrieve that")
                else:
                    await self.bot.say("I couldn't find an embed by that name.")
            else:
                await self.bot.say("I don't have any embeds stored for this server")
        else:
            await self.bot.say("I was expecting the name of the embed you wanted.")

    @embed.command(name="list", pass_context=True, no_pm=True)
    async def embed_list(self, ctx):

        ems = None
        server = ctx.message.server
        if server.id in self.settings:
            ems = self.settings[server.id].keys()
            if len(ems) > 0:
                await self.bot.say("Embed names for this server: {}".format(ems))
            else:
                await self.bot.say("No embeds found for this server.")
        else:
            await self.bot.say("No embeds found for this server.")






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
    n = GetHelp(bot)
    bot.add_cog(n)
