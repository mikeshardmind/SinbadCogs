import os
import asyncio  # noqa: F401
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


class ReportTool:
    """custom cog for a configureable report system."""
#   this is basically just a quick mod of my suggestionbox cog

    __author__ = "mikeshardmind"
    __version__ = "1.3"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/reporttool/settings.json')
        for s in self.settings:
            self.settings[s]['usercache'] = []

    def save_json(self):
        dataIO.save_json("data/reporttool/settings.json", self.settings)

    @commands.group(name="setreport", pass_context=True, no_pm=True)
    async def setreport(self, ctx):
        """configuration settings"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    def initial_config(self, server_id):
        """makes an entry for the server, defaults to turned off"""

        if server_id not in self.settings:
            self.settings[server_id] = {'inactive': True,
                                        'output': [],
                                        'cleanup': False,
                                        'usercache': [],
                                        'multiout': False
                                        }
            self.save_json()

    @checks.admin_or_permissions(Manage_server=True)
    @setreport.command(name="fixcache", pass_context=True, no_pm=True)
    async def fix_cache(self, ctx):
        """use this if the bot gets stuck not recording your response"""
        self.initial_config(ctx.message.server.id)
        self.settings[server.id]['usercache'] = []
        self.save_json()

    @checks.admin_or_permissions(Manage_server=True)
    @setreport.command(name="output", pass_context=True, no_pm=True)
    async def setoutput(self, ctx, chan: discord.Channel):
        """sets the output channel(s)"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if server != chan.server:
            return await self.bot.say("Stop trying to break this")
        if chan.type != discord.ChannelType.text:
            return await self.bot.say("That isn't a text channel")
        if chan.id in self.settings[server.id]['output']:
            return await self.bot.say("Channel already set as output")

        if self.settings[server.id]['multiout']:
            self.settings[server.id]['output'].append(chan.id)
            self.save_json()
            return await self.bot.say("Channel added to output list")
        else:
            self.settings[server.id]['output'] = [chan.id]
            self.save_json()
            return await self.bot.say("Channel set as output")

    @checks.admin_or_permissions(Manage_server=True)
    @setreport.command(name="toggleactive", pass_context=True, no_pm=True)
    async def report_toggle(self, ctx):
        """Toggles whether the Reporting tool is enabled or not"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        self.settings[server.id]['inactive'] = \
            not self.settings[server.id]['inactive']
        self.save_json()
        if self.settings[server.id]['inactive']:
            await self.bot.say("Reporting disabled.")
        else:
            await self.bot.say("Reporting enabled.")

    @commands.command(name="report", pass_context=True)
    async def makereport(self, ctx):
        "Follow the prompts to make a report"
        author = ctx.message.author
        server = ctx.message.server

        if server.id not in self.settings:
            return await self.bot.say("Reporting is not currently  "
                                      "configured for this server.")
        if self.settings[server.id]['inactive']:
            return await self.bot.say("Reporting is not currently "
                                      "enabled on this server.")

        if author.id in self.settings[server.id]['usercache']:
            return await self.bot.say("Finish making your prior report "
                                      "before making an additional one")

        await self.bot.say("I will message you to collect information")
        self.settings[server.id]['usercache'].append(author.id)

        dm = await self.bot.send_message(author,
                                         "Please respond to this message"
                                         "with your Report.\nYour "
                                         "Report should be a single "
                                         "message")

        message = await self.bot.wait_for_message(channel=dm.channel,
                                                  author=author, timeout=120)

        if message is None:
            await self.bot.send_message(author, "I can't wait forever, "
                                                "try again when ready")
            self.settings[server.id]['usercache'].remove(author.id)
            self.save_json()
        else:
            await self.send_report(message, server)

            await self.bot.send_message(author, "Your report was submitted.")

    async def send_report(self, message, server):

        author = message.author
        report = message.clean_content
        timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
        avatar = author.avatar_url if author.avatar \
            else author.default_avatar_url

        em = discord.Embed(description=report,
                           color=discord.Color.purple())
        em.set_author(name='Report from {}'.format(author.name),
                      icon_url=avatar)
        em.set_footer(text='Report made at {} UTC'.format(timestamp))

        for output in self.settings[server.id]['output']:
            where = server.get_channel(output)
            if where is not None:
                    await self.bot.send_message(where, embed=em)

        self.settings[server.id]['usercache'].remove(author.id)
        self.save_json()


def check_folder():
    f = 'data/reporttool'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/reporttool/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = ReportTool(bot)
    bot.add_cog(n)
