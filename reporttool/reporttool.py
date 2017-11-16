import pathlib
import asyncio  # noqa: F401
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from cogs.utils.chat_formatting import box, pagify

path = 'data/reportool'


class ReportTool:
    """custom cog for a configureable report system."""

    __author__ = "mikeshardmind (Sinbad#0413)"
    __version__ = "1.4.2"

    def __init__(self, bot):
        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + 'settings.json')
        except Exception:
            self.settings = {}
        for s in self.settings:
            self.settings[s]['usercache'] = []

    def save_json(self):
        dataIO.save_json(path + 'settings.json', self.settings)

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

    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.command(name="report", pass_context=True)
    async def makereport(self, ctx):
        "Follow the prompts to make a report"
        author = ctx.message.author
        try:
            server = author.server
        except AttributeError:
            server = await self.discover_server(author)
        if server is None:
            return

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

    async def discover_server(self, author: discord.User):

        shared_servers = []
        for server in self.bot.servers:
            x = server.get_member(author.id)
            if x is not None:
                shared_servers.append(server)
        output = ""
        servers = sorted(shared_servers, key=lambda s: s.name)
        for i, server in enumerate(servers, 1):
            output += "{}: {}\n".format(i, server.name)
        output += "\npick the server to make a report in by its number."

        for page in pagify(output, delims=["\n"]):
            dm = await self.bot.send_message(author, box(page))

        message = await self.bot.wait_for_message(channel=dm.channel,
                                                  author=author, timeout=15)
        if message is not None:
            try:
                message = int(message.content.strip())
                server = servers[message - 1]
            except ValueError:
                await self.bot.send_message(author,
                                            "That wasn't a valid choice")
                return None
            except IndexError:
                await self.bot.send_message(author,
                                            "That wasn't a valid choice")
                return None
            else:
                return server
        else:
            await self.bot.say("You took too long, try again later")
            return None

    async def send_report(self, message, server):

        author = server.get_member(message.author.id)
        report = message.clean_content
        avatar = author.avatar_url if author.avatar \
            else author.default_avatar_url

        em = discord.Embed(description=report,
                           color=discord.Color.purple())
        em.set_author(name='Report from {0.display_name}'.format(author),
                      icon_url=avatar)
        em.set_footer(text='{0.id}'.format(author))

        for output in self.settings[server.id]['output']:
            where = server.get_channel(output)
            if where is not None:
                    await self.bot.send_message(where, embed=em)

        self.settings[server.id]['usercache'].remove(author.id)
        self.save_json()


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = ReportTool(bot)
    bot.add_cog(n)
