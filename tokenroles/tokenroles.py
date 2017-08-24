import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import box, pagify
from .utils import checks
import random
import string


class TokenRoles:
    """Cog implementing token and/or pw based role access"""

    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/tokenroles/settings.json')

    def initial_config(self, server_id):
        if server_id not in self.settings:
            self.settings[server_id] = {'passcodes': {},
                                        'tokens': {},
                                        'active': False
                                        }
            self.save_json()

    def save_json(self):
        dataIO.save_json("data/tokenroles/settings.json", self.settings)

    @checks.admin_or_permissions(manage_roles=True)
    @commands.group(name="tokenset", no_pm=True, pass_context=True)
    async def tokenset(self, ctx):
        """Configuration options"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.serverowner_or_permissions(administrator=True)
    @tokenset.command(name="toggleactive", no_pm=True, pass_context=True)
    async def activetoggle(self, ctx):
        """toggle active"""

        server = ctx.message.server
        self.initial_config(server.id)
        self.settings[server.id]['active'] = \
            not self.settings[server.id]['active']
        self.save_json()
        if self.settings[server.id]['active']:
            await self.bot.say("Activated. Be careful with this.")
        else:
            await self.bot.say("Yeah, probably for the best.")

    @commands.cooldown(1, 5, commands.BucketType.server)
    @commands.command(name="usetoken", no_pm=True, pass_context=True)
    async def usetoken(self, ctx, token: str):
        """use a role token"""
        server = ctx.message.server
        author = ctx.message.author
        self.initial_config(server.id)
        if not self.settings[server.id]['active']:
            return await self.bot.say("This is inactive.")

        rid = self.settings[server.id]['tokens'].get(token, None)
        if rid:
            role = [r for r in server.roles if r.id == rid]
            self.settings[server.id]['tokens'].pop(token, None)
            self.save_json()
            await self.bot.add_roles(author, *role)

    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.command(name="usepasscode", no_pm=True, pass_context=True)
    async def use_passcode(self, ctx):
        """
        begin interactive password usage,
        must have messages from server members enabled
        """

        author = ctx.message.author
        server = ctx.message.server
        self.initial_config(server.id)
        if not self.settings[server.id]['active']:
            return await self.bot.say("This is inactive.")
        dm = await self.bot.send_message(author, "passcode?")

        msg = await self.bot.wait_for_message(channel=dm.channel,
                                              author=author, timeout=60)

        if msg:
            code = msg.content.strip()
            rid = self.settings[server.id]['passcodes'].get(code, None)
            if rid:
                role = [r for r in server.roles if r.id == rid]
                if role:
                    await self.bot.add_roles(author, *role)
                else:
                    await self.bot.send_message(author, "Failure.")
            else:
                await self.bot.send_message(author, "Failure.")
        else:
            await self.bot.send_message(author, "Try again when you have it")

    @checks.admin_or_permissions(manage_roles=True)
    @tokenset.command(name="maketoken", no_pm=True, pass_context=True)
    async def maketoken(self, ctx, role: discord.Role):
        """
        makes a single use token for granting a role
        user must be a mod, admin, or have manage roles
        they cannot make tokens for roles higher than their own highest
        """

        author = ctx.message.author
        server = ctx.message.server
        if not self.settings[server.id]['active']:
            return await self.bot.say("This is inactive.")
        if author.top_role < role:
            return await self.bot.say("Oh no you don't. You can't make a token"
                                      " for a role higher than yourself")

        token = ''.join([random.choice(string.ascii_letters + string.digits)
                         for n in range(32)])

        self.initial_config(server.id)
        self.settings[server.id]['tokens'][token] = role.id
        self.save_json()
        await self.bot.send_message(author, "Token\n`{}`".format(token))

    @checks.admin_or_permissions(manage_roles=True)
    @tokenset.command(name="invalidate", no_pm=True, pass_context=True)
    async def invalidate(self, ctx, code: str):
        """invalidates a code or token"""
        server = ctx.message.server
        self.initial_config(server.id)
        if not self.settings[server.id]['active']:
            return await self.bot.say("This is inactive.")
        self.settings[server.id]['tokens'].pop(code, None)
        self.save_json()

        self.settings[server.id]['passcodes'].pop(code, None)
        self.save_json()

    @checks.admin_or_permissions(manage_roles=True)
    @tokenset.command(name="makepasscode", no_pm=True, pass_context=True)
    async def make_passcode(self, ctx, role: discord.Role, rand=False):
        """makes a reusable passcode for a role"""

        author = ctx.message.author
        server = ctx.message.server

        self.initial_config(server.id)
        if not self.settings[server.id]['active']:
            return await self.bot.say("This is inactive.")

        if author.top_role < role:
            return await self.bot.say("Oh no you don't. You can't make a pass"
                                      "code for a role higher than yourself")

        if rand:
            passcode = ''.join([random.choice(string.ascii_letters
                                              + string.digits)
                                for n in range(32)])
            await self.bot.send_message(author, "random passcode"
                                        "\n`{}`".format(token))
        else:
            dm = await self.bot.send_message(author, "enter desired passcode.")

            msg = await self.bot.wait_for_message(channel=dm.channel,
                                                  author=author, timeout=60)
            if msg is not None:
                passcode = msg.content.strip()
            else:
                return await self.bot.say("Try again when you are ready")

        self.settings[server.id]['passcodes'][passcode] = role.id
        self.save_json()


def check_folder():
    f = 'data/tokenroles'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/tokenroles/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = TokenRoles(bot)
    bot.add_cog(n)
