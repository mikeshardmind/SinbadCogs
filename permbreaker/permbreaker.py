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

    Danger: Unload this cog then restart the bot to get old checks back.
    """

    def __init__(self, bot):
        self.bot = bot
        if dataIO.is_valid_json('data/permbreaker/commands.json'):
            self.settings = dataIO.load_json('data/permbreaker/commands.json')
        else:
            self.settings = {}
        self.modify_commands()

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
        types = self.modify_command(command_object)
        self.settings[command_object.name] = {'snowflakes': IDs,
                                              'types': types}
        self.save_json()
        await self.bot.say("checks modified.")

    def modify_commands(self):
        for k, v in self.settings.items():
            command_object = self.bot.get_command(k)
            if command_object is None:
                continue
            self.settings[k]['types'] = self.modify_command(command_object)
            self.save_json()

    def modify_command(self, command):
        own, srvown, adm, mod = False, False, False, False
        for i in range(0, len(command.checks)):
            some_check = command.checks.pop(i)
            if some_check.__repr__().startswith('<function is_owner_check'):
                own = True
            elif some_check.__repr__().startswith(
                    '<function serverowner_or_permissions.<locals>.predicate'):
                srvown = True
            elif some_check.__repr__().startswith(
                    '<function admin_or_permissions.<locals>.predicate'):
                adm = True
            elif some_check.__repr__().startswith(
                    '<function mod_or_permissions.<locals>.predicate'):
                mod = True
            else:
                command.checks.insert(i, some_check)
            if own or srvown or adm or mod:
                command.checks.insert(i, ModifiedCheck(command))

        return {'owner': own, "srv_owner": srvown, "admin": adm, "mod": mod}

    def __check(self, ctx):
        command = ctx.command.name
        author = ctx.message.author
        server = ctx.message.server
        if command not in self.settings:
            return True

        snowflakes = self.settings[command]['snowflakes']
        types = self.settings[command]['types']
        a_snowflakes = [author.id]
        if server is not None:
            a_snowflakes.extend([r.id for r in author.roles])

        if not set(a_snowflakes).isdisjoint(snowflakes):
            return True

        if types['owner']:
            return author.id == settings.owner or \
                author.id in ctx.bot.settings.co_owners
        if types['srv_owner']:
            return ctx.message.server.owner.id == author.id
        if server is not None:
            if types['admin']:
                admin_role = settings.get_server_admin(server).lower()
                role = discord.utils.find(
                    lambda r: r.name.lower() == admin_role, author.roles)
                return role is not None
            if types['mod']:
                mod_role = settings.get_server_mod(server).lower()
                admin_role = settings.get_server_admin(server).lower()
                role = discord.utils.find(
                    lambda r: r.name.lower()
                    in (mod_role, admin_role), author.roles)
                return role is not None

        return False


class ModifiedCheck:

    def __init__(self, command):
        self.command = command

    def __call__(self, ctx):
        self.ctx = ctx
        pbreaker = ctx.bot.get_cog('PermBreaker')
        # Break commands rather than allow arbitrary usage
        if pbreaker is None or not hasattr(pbreaker, '__check'):
            return False


def setup(bot):
    pathlib.Path('data/permbreaker').mkdir(parents=True, exist_ok=True)
    bot.add_cog(PermBreaker(bot))
