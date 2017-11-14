import discord
import pathlib
import itertools
from cogs.utils.dataIO import dataIO
from discord.ext import commands
from .utils import checks
from .utils.chat_formatting import pagify

path = 'data/permbreaker'


class PermBreaker:
    """
    cog for allowing bypass of checks on commands on a user by user basis
    This has security implications, use with care
    """

    def __init__(self, bot):
        self.bot = bot
        if dataIO.is_valid_json(path + '/settings.json'):
            self.settings = dataIO.load_json(path + '/settings.json')
        else:
            self.settings = {}

    def save_settings(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    @checks.is_owner()
    @commands.group(name='pbreak', pass_context=True)
    async def pbreak(self, ctx):
        """
        Settings for PermBreaker
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @pbreak.group(name='role', pass_context=True)
    async def pbreak_role(self, ctx):
        """"
        role specific settings
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @pbreak_role.command(name="allow", pass_context=True)
    async def pbreak_role_allow(self, ctx, command_name, *roles: discord.Role):
        """
        allow (a) specifc role(s) to use a command

        multiword commands need to be enclosed in quotes

        multiword roles also need to be enclosed in quotes
        This has security implications, be careful with it
        """
        if len(roles) == 0:
            return await self.bot.send_cmd_help(ctx)
        com = self.bot.get_command(command_name)
        if com is None:
            return await self.bot.say("No such command")
        if com.cog_name == 'PermBreaker':
            return await self.bot.say(
                "If you are going to allow this, "
                "you may as well just make them a coowner")

        current = self.settings.get(com.name, [])
        current.extend([x.id for x in roles])
        self.settings[com.name] = current
        self.save_settings()

        await self.bot.say('Bypass made')

    @pbreak.command(name='allow', pass_context=True)
    async def pbreak_allow(
            self, ctx, command_name, *who: discord.Member):
        """
        Allows a list of users use a command without needing
        to meet the normal checks requirements of the command

        multiword commands need to be enclosed in quotes

        This has security implications, be careful with it
        """
        if len(who) == 0:
            return await self.bot.send_cmd_help(ctx)
        com = self.bot.get_command(command_name)
        if com is None:
            return await self.bot.say("No such command")
        if com.cog_name == 'PermBreaker':
            return await self.bot.say(
                "If you are going to allow this, "
                "you may as well just make them a coowner")

        current = self.settings.get(com.name, [])
        current.extend([x.id for x in who])
        self.settings[com.name] = current
        self.save_settings()

        await self.bot.say('Bypass made')

    @pbreak_role.command(name="disallow", pass_context=True)
    async def pbreak_role_disallow(
            self, ctx, command_name, *roles: discord.Role):
        """
        removes roles from being allowed to use a command

        multiword commands need to be enclosed in quotes

        the same applies to mutiword roles
        """
        if len(roles) == 0:
            return await self.bot.send_cmd_help(ctx)
        com = self.bot.get_command(command_name)
        if com is None:
            return await self.bot.say("No such command")

        if com.name not in self.settings:
            return await self.bot.say('No settings for this command to modify')

        self.settings[com.name] = [x for x in self.settings[com.name]
                                   if x not in [y.id for y in roles]]
        self.save_settings()

        await self.bot.say('Settings updated')

    @pbreak.command(name='disallow', pass_context=True)
    async def pbreak_disallow(self, ctx, command_name, *who: discord.Member):
        """
        removes people from being allowed to use a command

        multiword commands need to be enclosed in quotes
        """
        if len(who) == 0:
            return await self.bot.send_cmd_help(ctx)
        com = self.bot.get_command(command_name)
        if com is None:
            return await self.bot.say("No such command")

        if com.name not in self.settings:
            return await self.bot.say('No settings for this command to modify')

        self.settings[com.name] = [x for x in self.settings[com.name]
                                   if x not in [y.id for y in who]]
        self.save_settings()

        await self.bot.say('Settings updated')

    @pbreak_role.command(name='disallowall', pass_context=True)
    async def pbreak_role_disallowall(
            self, ctx, command_name, *roles: discord.Role):
        """
        removes any entries for a role
        """
        if len(roles) == 0:
            return await self.bot.send_cmd_help(ctx)

        for k, v in self.settings.items():
            self.settings[k] = [x for x in v if x not in [y.id for y in roles]]

        await self.bot.say('Settings updated')

    @pbreak.command(name='disallowall', pass_context=True)
    async def pbreak_disallowall(
            self, ctx, *who: discord.Member):
        """
        removes any entries for a user
        """
        if len(who) == 0:
            return await self.bot.send_cmd_help(ctx)

        for k, v in self.settings.items():
            self.settings[k] = [x for x in v if x not in [y.id for y in who]]

        await self.bot.say('Settings updated')

    @pbreak.command(name='clear', pass_context=True)
    async def pbreak_clear(self, ctx, command_name):
        """
        clears the allowed list for a command
        multiword commands need to be enclosed in quotes
        """

        com = self.bot.get_command(command_name)
        if com is None:
            return await self.bot.say("No such command")

        self.settings[com.name] = []
        self.save_settings()

        await self.bot.say('Allowed list cleared')

    @pbreak.command(name='clearall', pass_context=True)
    async def pbreak_clearall(self, ctx):
        """clears settings"""

        self.settings = {}
        self.save_settings()
        await self.bot.say('Settings cleared')

    @pbreak.command(name='showconfig', pass_context=True)
    async def pbreak_showconfig(self, ctx):
        """
        gets the current bypasses and prints them
        """

        data = {}
        who = [x for x in self.bot.get_all_members()]
        roles = []
        for server in self.bot.servers:
            roles.extend(server.roles)
        for k, v in self.settings.items():
            users = unique([u for u in who if u.id in v])
            roles = [r for r in roles if r.id in v]
            data[k] = {'u': users, 'r': roles}

        output = ""
        for k, v in data.items():
            output += "\n\nOverrides for '{}'".format(k)
            output += "\nUsers: "
            for user in v['u']:
                output += "{} ".format(user.mention)
            output += "\nRoles: "
            for role in v['r']:
                output += "\nRole: {0.name} | Server: {0.server.name}".format(
                    role)

        if len(output) == 0:
            return await self.bot.say('No config set yet')
        for page in pagify(output.strip()):
            await self.bot.whisper(page)

    async def maybe_run_anyway(self, error, ctx):
        if not isinstance(error, commands.CheckFailure):
            return
        if ctx.cog == self:
            # At the point where allowing others to use this, just make them
            # a coowner
            return

        if self.can_bypass_checks(ctx):
            await self.bypass_checks(ctx)

    def can_bypass_checks(self, ctx):

        if ctx.command.name not in self.settings:
            return False
        flakes = self.settings[ctx.command.name]
        if ctx.message.author.id in flakes:
            return True
        elif ctx.message.server:
            role_flakes = [r.id for r in ctx.message.author.roles]
            return not set(role_flakes).isdisjoint(flakes)
        else:
            return False

    async def bypass_checks(self, ctx):
        # please don't kill me Danny
        await ctx.command._parse_arguments(ctx)
        injected = commands.core.inject_context(ctx, ctx.command.callback)
        await injected(*ctx.args, **ctx.kwargs)


def unique(a):
    indices = sorted(range(len(a)), key=a.__getitem__)
    indices = set(next(it) for k, it in
                  itertools.groupby(indices, key=a.__getitem__))
    return [x for i, x in enumerate(a) if i in indices]


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = PermBreaker(bot)
    bot.add_listener(n.maybe_run_anyway, "on_command_error")
    bot.add_cog(n)
