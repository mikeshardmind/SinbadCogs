import pathlib
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from __main__ import settings

path = 'data/roleblacklist'


class RoleBlacklist:
    """
    Role based blacklist
    """

    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0001)"

    def __init__(self, bot):
        self.bot = bot
        self.load_roles()

    def load_roles(self):
        try:
            self.roles = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.roles = {}

    def save_roles(self):
        dataIO.save_json(path + '/settings.json', self.roles)

    @commands.command(pass_context=True, name='roleblacklist', no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def set_forbidden_role(self, ctx, *roles: discord.Role):
        """
        sets the role(s) which cannot use the bot
        multi word roles should be surrounded with quotes

        WARNING: make sure people cannot remove any of these roles
        with another bot or something
        """
        server = ctx.message.server
        if len(roles) > 0:
            self.roles[server.id] = [r.id for r in roles]
            self.save_roles()
            await self.bot.say('Role(s) set')
        else:
            await self.bot.send_cmd_help(ctx)

    def __check(self, ctx):
        allowed = False
        author = ctx.message.author
        try:
            server = author.server
        except AttributeError:
            return True
        allowed |= author.id == settings.owner
        if isinstance(author, discord.Member):
            allowed |= not any(
                r.id in self.roles[server.id]
                for r in author.roles
            )
        return allowed


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    bot.add_cog(RoleBlacklist(bot))
