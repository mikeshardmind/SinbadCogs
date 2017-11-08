import discord
import pathlib
from __main__ import settings
from cogs.utils.dataIO import dataIO
from discord.ext import commands
from .utils import checks


class PermBreaker:
    """
    Intentionally modify the checks on commands
    modifies owner, server_owner, admin, mod (+ x_or_perms)
    to additionally check for any matching role ID or user ID
    granular by command

    when modifying a  x_or_perms check, the "or perms" portion will be dropped
    because I'm lazy af, and the use case where a command has that and still
    needs to be overridden for some people doesn't make sense.

    Also being really lazy and rather than track down a pickle error being
    raised by deepcopy, I'm going to hope anyone using this plans on it for
    long term usage. Reload affected cogs after unloading this one to get
    old checks back.
    """

    def __init__(self, bot):
        self.bot = bot
        if dataIO.is_valid_json('data/permbreaker/commands.json'):
            self.settings = dataIO.load_json('data/permbreaker/commands.json')
        else:
            self.settings = {}

        for k, v in self.settings.items():
            c = bot.get_command(k)
            if c:
                self.modify_command(c)

    def save_json(self):
        dataIO.save_json("data/permbreaker/commands.json", self.settings)

    @commands.command(name="modifycheck", pass_context=True)
    @checks.is_owner()  # just for help formatting, sanity check in func
    async def modifycheck(self, ctx, com: str, *IDs: str):
        """
        takes a command by name
        (if its a multi word command i.e. a command that is part of a group,
        use quotes around it)

        and a list of valid IDs to be additionally allowed to use the command
        IDs may be role IDs or User IDs
        """
        # Sanity check since this command should probably never be modified
        if ctx.message.author.id != settings.owner and \
                ctx.message.author.id not in ctx.bot.settings.co_owners:
            return

        command_object = self.bot.get_command(com.split()[-1])
        if command_object is None:
            return await self.bot.say("No such command")
        self.settings[command_object.name] = IDs
        self.modify_command(command_object)

        self.save_json()
        await self.bot.say(
            "checks modified. reload the cog containing the "
            "command to restore old check")

    def modify_command(self, command):
        for i in range(0, len(command.checks)):
            some_check = command.checks.pop(i)
            if some_check.__repr__().startswith(
                    '<function is_owner_check'):
                command.checks.insert(i, NewOwnerCheck(command))
            elif some_check.__repr__().startswith(
                    '<function serverowner_or_permissions.<locals>.predicate'):
                command.checks.insert(i, NewServerOwnerCheck(command))
            elif some_check.__repr__().startswith(
                    '<function admin_or_permissions.<locals>.predicate'):
                command.checks.insert(i, NewAdminCheck(command))
            elif some_check.__repr__().startswith(
                    '<function mod_or_permissions.<locals>.predicate'):
                command.checks.insert(i, NewModCheck(command))
            else:
                command.checks.insert(i, some_check)

    def is_listed(self, ctx):

        command = ctx.command.name
        author = ctx.message.author

        snowflakes = self.settings[command]
        if isinstance(author, discord.Member):
            author_snowflakes = [r.id for r in author.roles]
        else:
            author_snowflakes = []
        ret = not set(snowflakes).isdisjoint(author_snowflakes) \
            or author.id in snowflakes

        return ret


class NewOwnerCheck:

    def __init__(self, command):
        self.command = command

    def __call__(self, ctx):
        pbreaker = ctx.bot.get_cog('PermBreaker')
        _auth = ctx.message.author
        if pbreaker is None:
            return True

        ret = _auth.id == settings.owner \
            or _auth.id in ctx.bot.settings.co_owners \
            or pbreaker.is_listed(ctx)

        return ret


class NewServerOwnerCheck:

    def __init__(self, command):
        self.command = command

    def __call__(self, ctx):
        pbreaker = ctx.bot.get_cog('PermBreaker')
        _auth = ctx.message.author
        _srv = ctx.message.server
        if _srv is None:
            return False
        if pbreaker is None:
            return True

        ret = _auth.id == _srv.owner.id or pbreaker.is_listed(ctx)
        return ret


class NewAdminCheck:

    def __init__(self, command):
        self.command = command

    def __call__(self, ctx):
        pbreaker = ctx.bot.get_cog('PermBreaker')
        _auth = ctx.message.author
        _srv = ctx.message.server
        if _srv is None:
            return False
        if pbreaker is None:
            return True

        admin_role = settings.get_server_admin(_srv).lower()
        allowed = False
        allowed |= pbreaker.is_listed(ctx)
        allowed |= len([r for r in _auth.roles
                        if r.name.lower() == admin_role]) > 0
        return allowed


class NewModCheck:

        def __init__(self, command):
            self.command = command

        def __call__(self, ctx):
            pbreaker = ctx.bot.get_cog('PermBreaker')
            _auth = ctx.message.author
            _srv = ctx.message.server
            if _srv is None:
                return False
            if pbreaker is None:
                return True

            mod_role = settings.get_server_mod(_srv).lower()
            admin_role = settings.get_server_admin(_srv).lower()
            allowed = False
            allowed |= pbreaker.is_listed(ctx)
            allowed |= len([r for r in _auth.roles
                            if r.name.lower() == mod_role
                            or r.name.lower() == admin_role]) > 0
            return allowed


def setup(bot):
    pathlib.Path('data/permbreaker').mkdir(parents=True, exist_ok=True)
    bot.add_cog(PermBreaker(bot))
