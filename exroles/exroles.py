import discord
import pathlib
import logging
import itertools
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks
from cogs.utils.chat_formatting import pagify


log = logging.getLogger('red.ExRoles')


class ExRoleError(Exception):
    pass


class ExRoles:
    """
    Role exclusivity
    """

    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/exroles/settings.json')
        # mapping: ServerID -> Groupname -> list of role IDs

    def save_json(self):
        dataIO.save_json("data/exroles/settings.json", self.settings)

    def get_joinable(self, member: discord.Member):
        server = member.server

        if server.id not in self.settings:
            raise ExRoleError('No settings for this server')
            return

        available = []

        for k, v in self.settings[server.id].items():
            set_roles = [r for r in server.roles if r.id in v]
            if set(member.roles).isdisjoint(set_roles):
                available.extend(set_roles)

            else:
                for role in set_roles:
                    if role in available:
                        available.remove(role)

        return available

    @commands.group(name='exroleset', pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def exroleset(self, ctx):
        """
        config for ExRoles
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @exroleset.command(name='group', pass_context=True, no_pm=True)
    async def group(self, ctx, name: str, *roles: discord.Role):
        """
        setup a group by name with a list of roles which are both
        self assignable and mutually exclusive
        """
        srv = ctx.message.server
        rs = unique(roles)

        if len(rs) != len(roles):
            await self.bot.say(
                "You are a dumbass for putting the same role in "
                "multiple times, I fixed it for you.")

        if any(r for r in rs if r >= ctx.message.author.top_role):
            return await self.bot.say(
                "Aborting setup: You can't give away roles higher than yours")

        if srv.id not in self.settings:
            self.settings[srv.id] = {}

        self.settings[srv.id][name] = [r.id for r in rs]
        self.save_json()
        await self.bot.say('Group set')

    @commands.command(name='rjoin', pass_context=True, no_pm=True)
    async def join(self, ctx, role: discord.Role):
        """
        join a role
        """

        author = ctx.message.author

        try:
            avail = self.get_joinable(author)
        except ExRoleError as e:
            return await self.bot.say(e)

        if role not in avail:
            return await self.bot.say(
                "Role: {0.name} is not available to you, {1.mention}".format(
                    role, author))

        try:
            await self.bot.add_roles(author, role)
        except Exception as e:
            await self.bot.say("Something went wrong")
        else:
            await self.bot.say("Role assigned")

    @exroleset.command(name='audit', pass_context=True, no_pm=True)
    async def audit(self, ctx):
        """
        might take a while
        """

        output = ""
        srv = ctx.message.server
        if srv.id not in self.settings:
            return await self.bot.say('Nothing to audit here')
        for member in srv.members:
            for k, v in self.settings[srv.id].items():
                r_c = [r for r in member.roles if r.id in v]

                if len(r_c) > 1:
                    output += "\n{0.mention} : `{1}: {2}`".format(
                        member, k, [r.name for r in r_c])
        if output == "":
            return await self.bot.say('No issues found')

        msg = "A list of each user with conflicting roles for you to fix:" + \
            output

        for page in pagify(msg):
            await self.bot.say(page)


def unique(a):
    indices = sorted(range(len(a)), key=a.__getitem__)
    indices = set(next(it) for k, it in
                  itertools.groupby(indices, key=a.__getitem__))
    return [x for i, x in enumerate(a) if i in indices]


def ensure_path():
    pathlib.Path('data/exroles').mkdir(parents=True, exist_ok=True)
    f = 'data/exroles/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    ensure_path()
    bot.add_cog(ExRoles(bot))
