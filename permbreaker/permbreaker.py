import discord
import pathlib
import json
import time
from copy import deepcopy
from __main__ import settings
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
    """

    def __init__(self, bot):
        self.bot = bot
        for command in oldcommands:
            self.swap_command(command)

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

        pathlib.Path('data/permbreaker').mkdir(parents=True, exist_ok=True)

        if pathlib.Path('data/permbreaker/commands.json').is_file():
            try:
                with open('data/permbreaker/commands.json',
                          encoding='utf-8', mode="r") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        command_object = self.bot.get_command(com.split()[-1])
        if command_object is None:
            return await self.bot.say("No such command")

        if command_object.name not in oldcommands:
            self.swap_command(command_object)

        with open('data/permbreaker/commands.json',
                  encoding='utf-8', mode="w") as f:
            json.dump(
                data, f, indent=4, sort_keys=True, separators=(',', ' : '))

    def __unload(self):
        for command in oldcommands:
            self.bot.add_command(command)

    def swap_command(self, command):
        if command not in oldcommands:
            oldcommands.append(command)
        nc = self.modify_command(command)
        self.bot.remove_command(command.name)
        self.bot.add_command(nc)

    def modify_command(self, command, whitelisted_snowflake):
        botowner, srvowner, admin, mod = False, False, False, False
        new_com = deepcopy(command)
        new_com.checks.clear()
        for some_check in command.checks:
            if some_check.__repr__().starts_with(
                    '<function is_owner_check'):
                botowner |= True
            elif some_check.__repr__().starts_with(
                    '<function serverowner_or_permissions.<locals>.predicate'):
                srvowner |= True
            elif some_check.__repr__().starts_with(
                    '<function admin_or_permissions.<locals>.predicate'):
                admin |= True
            elif some_check.__repr__().starts_with(
                    '<function mod_or_permissions.<locals>.predicate'):
                mod |= True
            else:
                new_com.checks.append(some_check)

        if botowner:
            new_com.checks.append(NewOwnerCheck(command))
        if srvowner:
            new_com.checks.append(NewServerOwnerCheck(command))
        if admin:
            new_com.checks.append(NewAdminCheck(command))
        if mod:
            new_com.checks.append(NewModCheck(command))

        return new_com

    def is_listed(self, ctx):

        command = ctx.command.name
        author = ctx.message.author

        if pathlib.Path('data/permbreaker/commands.json').is_file():
            try:
                with open('data/permbreaker/commands.json',
                          encoding='utf-8', mode="r") as f:
                    data = json.load(f)
            except Exception:
                return False
            else:
                if data:
                    if command in data:
                        snowflakes = data[command].get('snowflakes', [])
        if not snowflakes:
            return False
        if len(snowflakes) == 0:
            return False

        author_snowflakes = [author.id]
        if isinstance(author, discord.Member):
            author_snowflakes.extend([r.id for r in author.roles])
        return not set(snowflakes).is_disjoint(author_snowflakes)


class NewOwnerCheck:

    def __init__(self, command):
        self.command = command

    def __call__(self, ctx):
        pbreaker = ctx.bot.get_cog('PermBreaker')
        _auth = ctx.message.author
        if pbreaker is None:
            return True

        return _auth.id == settings.owner \
            or _auth.id in ctx.bot.settings.co_owners \
            or pbreaker.is_listed(ctx)


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

        return _auth.id == _srv.owner.id or pbreaker.is_listed(ctx)


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
    # make sure there's time for commands to be loaded (for restarts...)
    time.sleep(10)
    pathlib.Path('data/permbreaker').mkdir(parents=True, exist_ok=True)
    global oldcommands
    oldcommands = []
    if pathlib.Path('data/permbreaker/commands.json').is_file():
        try:
            with open('data/permbreaker/commands.json',
                      encoding='utf-8', mode="r") as f:
                data = json.load(f)
        except Exception:
            pass
        else:
            if data:
                for k, v in data.items():
                    old = bot.get_command(k)
                    if old:
                        oldcommands.append(old)

    bot.add_cog(PermBreaker(bot))
