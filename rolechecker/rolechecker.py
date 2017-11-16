import pathlib
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from __main__ import settings

path = 'data/rolechecker'


class RoleChecker:
    """
    Require a role to use the bot
    """

    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        self.bot = bot
        self.load_roles()

    def load_roles(self):
        try:
            self.roles = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.roles = []

    def save_roles(self):
        dataIO.save_json(path + '/settings.json', self.roles)

    @commands.command()
    @checks.is_owner()
    async def set_required_role(self, ctx, *roles: discord.Role):
        """
        sets the role(s) required to use the bot
        multi word roles should be surrounded with quotes

        WARNING: make sure people cannot assign themselves any of these roles
        with another bot or something

        To disable this check, unload the cog
        """
        if len(roles) > 0:
            self.roles = [r.id for r in roles]
            self.save_roles()
            await self.bot.say('Role set')
        else:
            await self.bot.send_cmd_help(ctx)

    def __check(self, ctx):
        allowed = False
        author = ctx.message.author
        allowed |= author.id == settings.owner
        if isinstance(author, discord.Member):
            allowed |= len([r for r in author.roles
                            if r.id in self.roles]) > 0
        return allowed


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    bot.add_cog(RoleChecker(bot))
