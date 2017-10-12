import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from __main__ import settings


class RoleChecker:
    """
    Require a role to use the bot
    """

    def __init__(self, bot):
        self.bot = bot
        self.load_roles()

    def load_roles(self):
        self.roles = dataIO.load_json('data/rolechecker/settings.json')

    def save_roles(self):
        dataIO.save_json("data/rolechecker/settings.json", self.roles)

    @commands.command()
    @checks.is_owner()
    async def set_required_role(self, ctx, *roles: str):
        """
        sets the role(s) required to use the bot
        multi word roles should be surrounded with quotes

        WARNING:this is checked by name, so be sure people cant assign
        arbitrary role names to themselves with other bots

        to disable this check, unload the cog
        """
        if len(roles) > 0:
            self.roles = roles
            self.save_roles()
            await self.bot.say('Role set')
        else:
            await self.bot.send_cmd_help(ctx)

    async def __check(self, ctx):
        allowed = False
        author = ctx.message.author
        allowed |= author.id == settings.owner
        if isinstance(ctx.author, discord.Member):
            allowed |= len([r for r in author.roles
                            if r.name in self.roles]) > 0
        return allowed


def _ensure_fs():
    f = 'data/rolechecker'
    if not os.path.exists(f):
        os.makedirs(f)

    f = 'data/rolechecker/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    _ensure_fs()
    bot.add_cog(RoleChecker(bot))
