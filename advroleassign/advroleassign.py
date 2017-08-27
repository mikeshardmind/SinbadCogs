import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import box, pagify
from .utils import checks
import itertools
from datetime import datetime, timedelta
assert timedelta  # Pyflakes, shut up; I'm using it implicitly


class AdvRoleAssign:

    """
    Tool for setting up mutually exclusive self-assignable roles
    with optional lockout
    """
    __author__ = "mikeshardmind"
    __version__ = "2.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/advroleassign/settings.json')
        self.lockouts = {}

    def save_json(self):
        dataIO.save_json('data/advroleassign/settings.json', self.settings)

    def initial_config(self, server):
        if server.id not in self.settings:
            self.settings[server.id] = {'selfroles': [],
                                        'active': False,
                                        'lockout': 0,
                                        'rolerules': {},
                                        'ignoredroles': [],
                                        'version': 2
                                        }
        if self.settings[server.id].get('version', None) != 2:
            self.backwards_compatability()
        self.save_json()

    def backwards_compatability(self):
        for k, v in self.settings.items():
            if v.get('version', None) is None:
                self.upgrade_v1_to_v2(k)

    def upgrade_v1_to_v2(self, server_id):
        srv_sets = self.settings[server_id]
        srv_sets['rolerules'] = {}
        srv_sets['ignoredroles'] = []
        for role in srv_sets['selfroles']:
            srv_sets['rolerules'][role] = {'exclusiveto': [],
                                           'requiresany': [],
                                           'lockoutoverride': None
                                           }
            if role in srv_sets['exclusiveroles']:
                srv_sets['rolerules'][role]['exclusiveto'] = \
                    [r for r in srv_sets['exclusiveroles'] if r != role]

        for role in srv_sets['memberselfroles']:
            if role not in srv_sets['selfroles']:
                srv_sets['selfroles'].append(role)
                srv_sets['rolerules'][role] = {'exclusiveto': [],
                                               'requiresany': [],
                                               'lockoutoverride': None
                                               }
                if role in srv_sets['exclusiveroles']:
                    srv_sets['rolerules'][role]['exclusiveto'] = \
                        [r for r in srv_sets['exclusiveroles'] if r != role]

                srv_sets['rolerules'][role]['requiresany'] = \
                    [r for r in srv_sets['membershiproles'] if r != role]

        srv_sets.pop('exclusiveroles', None)
        srv_sets.pop('memberselfroles', None)
        srv_sets.pop('membershiproles', None)
        srv_sets.update({'version': 2})

        self.save_json()

    @checks.mod_or_permissions(manage_roles=True)
    @commands.group(name="advroleset", no_pm=True, pass_context=True)
    async def advroleset(self, ctx):
        """settings for advroleassign"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @advroleset.command(name="viewconfig", no_pm=True, pass_context=True)
    async def viewconfig(self, ctx):
        """sends you info on the current config"""
        server = ctx.message.server
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        output = ""

        output += "Enabled: {}".format(srv_sets['active'])
        output += "\n\n+ Information about self assignable roles"

        for role in server.roles:
            if role.id in srv_sets['selfroles']:
                output += "\n\n- Role name: {}".format(role.name)
                reqs = [r for r in server.roles if r.id in
                        srv_sets['rolerules'][role.id]['requiresany']]
                if len(reqs) > 0:
                    output += "\nRequires any of the following roles:"
                    for req in reqs:
                        output += "\n{}".format(req.name)
                excls = [r for r in server.roles if r.id in
                         srv_sets['rolerules'][role.id]['exclusiveto']]
                if len(excls) > 0:
                    output += "\nMutually exclusive to all of these roles:"
                    for excl in excls:
                        output += "\n{}".format(excl.name)

        for page in pagify(output, delims=["\n", ","]):
            await self.bot.send_message(ctx.message.author, box(page, "diff"))

    @advroleset.command(name="toggleactive", no_pm=True, pass_context=True)
    async def toggle_active(self, ctx):
        """
        toggles the ability for users to assign roles
        """
        server = ctx.message.server
        self.initial_config(server)
        self.settings[server.id]['active'] = \
            not self.settings[server.id]['active']
        self.save_json()

        if self.settings[server.id]['active']:
            await self.bot.say("Activated.")
        else:
            await self.bot.say("Deactivated.")

    @advroleset.command(name="ignorerole", pass_context=True, no_pm=True)
    async def ignorerole(self, ctx, role: discord.Role):
        """
        sets a role for which if a user has it, they cannot self assign
        a role
        """
        server = ctx.message.server
        self.initial_config(server)
        if role.id in self.settings[server.id]['ignoredroles']:
            await self.bot.say("I'm already ignoring that role")
        else:
            self.settings[server.id]['ignoredroles'].append(role.id)
            await self.bot.say("Role ignored")
        self.save_json()

    @advroleset.command(name="unignorerole", pass_context=True, no_pm=True)
    async def unignorerole(self, ctx, role: discord.Role):
        """
        unignore a role
        """
        server = ctx.message.server
        self.initial_config(server)
        if role.id not in self.settings[server.id]['ignoredroles']:
            await self.bot.say("I wasn't ignoring that role")
        else:
            self.settings[server.id]['ignoredroles'].remove(role.id)
            await self.bot.say("No longer ignoring that role.")
        self.save_json()

    @advroleset.command(name="setlockout", no_pm=True, pass_context=True)
    async def set_lockout(self, ctx, seconds: int):
        """
        sets the minimum amount of time inbetween switching from one exclusive
        role to another (-1 to disallow switching)
        """

        server = ctx.message.server
        self.initial_config(server)
        self.settings[server.id]['lockout'] = seconds
        self.save_json()

        if seconds == -1:
            await self.bot.say("Lockout is indefinite")
        else:
            await self.bot.say("Lockout on switching between exclusive roles "
                               "is set to {} second(s)".format(seconds))

    @advroleset.command(name="addselfrole", no_pm=True, pass_context=True)
    async def advset_add_selfrole(self, ctx, role: discord.Role):
        """add a role that anyone can self assign"""

        server = ctx.message.server
        user = ctx.message.author
        if user.top_role < role:
            return await self.bot.say("you can't give away roles higher "
                                      "than yourself")
        if role > self.bot.client.top_role:
            return await self.bot.say("I will be unable to do this do to the "
                                      "role being above me in the role "
                                      "heirarchy")

        self.initial_config(server)
        if role.id not in self.settings[server.id]['selfroles']:
            self.settings[server.id]['selfroles'].append(role.id)
            self.save_json()
            await self.bot.say("Role added to self assignable list")
        else:
            await self.bot.say("That role is already self assignable")

    @advroleset.command(name="requirerole", no_pm=True, pass_context=True)
    async def advset_requireroles(self, ctx, role: discord.Role,
                                  *roles: discord.Role):
        """
        Takes a list of roles. The first role is the role to restrict.
        Every role after it is a role that allows you to assign the first role
        call with only a single role to clear the requirement.
        """

        server = ctx.message.server
        self.initial_config(server)
        if role.id not in self.settings[server.id]['selfroles']:
            return await self.bot.say("This role is not self assignable ")
        if role in roles:
            await self.bot.say("A role can't be it's own requirement. "
                               "Ignoring that it was given for itself")
            roles.remove(role)
        if role.id not in self.settings[server.id]['rolerules']:
            self.settings[server.id]['rolerules'][role.id] = \
                {'exclusiveto': [],
                 'requiresany': []
                 }
        self.settings[server.id]['rolerules'][role.id]['requiresany'] = \
            unique([r.id for r in roles])
        if len(roles) == 0:
            await self.bot.say("This role has no requirements")
        else:
            await self.bot.say("Role requirements set")
        self.save_json()

    @advroleset.command(name="mutuallyexclusive",
                        no_pm=True, pass_context=True)
    async def advset_mutualexclusive(self, ctx, *roles: discord.Role):
        """
        Designate a list of roles which are mutually exclusive to eachother
        if called with only a single role, instead clears any mutual
        exclusivity settings for that role
        """

        server = ctx.message.server
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        roles = unique(roles)
        if len(roles) == 0:
            return await self.bot.send_cmd_help(ctx)
        if len(roles) == 1:
            role = roles[0]
            if role.id in srv_sets['rolerules']:
                srv_sets['rolerules'][role.id]['exclusiveto'] = []
            for k, v in srv_sets['rolerules'].items():
                if role.id in v['exclusiveto']:
                    v['exclusiveto'].remove(role.id)
            await self.bot.say("Exclusivity settings for that role cleared.")
        else:
            for role in roles:
                a = [r.id for r in roles if r != role]
                if role.id not in srv_sets['rolerules']:
                    srv_sets['rolerules'][role.id] = \
                        {'exclusiveto': [],
                         'requiresany': []
                         }
                srv_sets['rolerules'][role.id]['exclusiveto'].extend(a)
                srv_sets['rolerules'][role.id]['exclusiveto'] = \
                    unique(srv_sets['rolerules'][role.id]['exclusiveto'])

            await self.bot.say("Exclusivity set")
        self.save_json()

    @advroleset.command(name="delselfrole", no_pm=True, pass_context=True)
    async def advset_rem_selfrole(self, ctx, role: discord.Role):
        """remove a role from the self assignable list"""

        server = ctx.message.server
        self.initial_config(server)
        if role.id in self.settings[server.id]['selfroles']:
            self.settings[server.id]['selfroles'].remove(role.id)
            self.save_json()
            try:
                self.settings[server.id]['rolerules'].remove(role.id)
            except ValueError:
                pass
            await self.bot.say("That role is no longer self assignable")
        else:
            await self.bot.say("That role was not self assignable")

    @commands.group(name="advrole", no_pm=True, pass_context=True)
    async def advrole(self, ctx):
        """commands for self assigning roles"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @advrole.command(name="list", no_pm=True, pass_context=True)
    async def listroles(self, ctx):
        """list roles which are available to you for self assignment"""
        user = ctx.message.author
        server = ctx.message.server
        server_roles = server.roles
        now = datetime.utcnow()
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        ignoredroles = [r for r in server_roles
                        if r.id in srv_sets['ignoredroles']]
        locked_out = False
        conflicting_roles = []
        unqualified_roles = []

        if not srv_sets['active']:
            return await self.bot.say("No roles currently self assignable.")

        if not set(ignoredroles).isdisjoint(user.roles):
            return await self.bot.say("You aren't allowed to assign a role")

        self_roles = [r for r in server_roles if r.id in
                      srv_sets['selfroles']]

        self_roles = [r for r in self_roles if r not in user.roles]

        if server.id not in self.lockouts:
            self.lockouts[server.id] = {}
        if user.id in self.lockouts[server.id]:
            tdelta = now - srv_sets[user.id]
            if tdelta.seconds < srv_sets['lockout']:
                locked_out = True
        if srv_sets['lockout'] == -1:
            locked_out = True

        for x in self_roles:
            test_exclusive = [r for r in server_roles if r.id in
                              srv_sets['rolerules'][x.id]['exclusiveto']]

            if not set(test_exclusive).isdisjoint(user.roles):
                conflicting_roles.append(x)

            req_for_x = [r for r in server_roles if r.id in
                         srv_sets['rolerules'][x.id]['requiresany']]

            if len(req_for_x) > 0 and set(req_for_x).isdisjoint(user.roles):
                unqualified_roles.append(x)

        self_roles = [r for r in self_roles if r not in unqualified_roles]

        if locked_out:
            self_roles = [r for r in self_roles if r not in conflicting_roles]

        output = "The following roles are available to you:\n"
        for role in self_roles:
            if role not in user.roles:
                output += "\n{}".format(role.name)

        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(box(page))

    @advrole.command(name="join", no_pm=True, pass_context=True)
    async def joinrole(self, ctx, role: discord.Role):
        """joins a role which is available to you for self assignment"""
        user = ctx.message.author
        server = ctx.message.server
        server_roles = server.roles
        now = datetime.utcnow()
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        ignoredroles = [r for r in server_roles
                        if r.id in srv_sets['ignoredroles']]
        locked_out = False
        conflicting_roles = []
        unqualified_roles = []

        if not srv_sets['active']:
            return await self.bot.say("No roles currently self assignable.")

        if role in user.roles:
            return await self.bot.say("You already have that role.")

        if not set(ignoredroles).isdisjoint(user.roles):
            return await self.bot.say("You aren't allowed to assign a role")

        self_roles = [r for r in server_roles if r.id in
                      srv_sets['selfroles']]

        self_roles = [r for r in self_roles if r not in user.roles]

        if server.id not in self.lockouts:
            self.lockouts[server.id] = {}
        if user.id in self.lockouts[server.id]:
            tdelta = now - srv_sets[user.id]
            if tdelta.seconds < srv_sets['lockout']:
                locked_out = True
        if srv_sets['lockout'] == -1:
            locked_out = True

        for x in self_roles:
            if x == role:
                test_exclusive = [r for r in server_roles if r.id in
                                  srv_sets['rolerules'][x.id]['exclusiveto']]
                rms = list(set(test_exclusive).intersection(user.roles))
                conflicting_roles.append(rms)
            elif x in user.roles:
                test_exclusive = [r for r in server_roles if r.id in
                                  srv_sets['rolerules'][role.id]['exclusiveto']]
                if x in test_exclusive:
                    conflicting_roles.append(x)

            req_for_x = [r for r in server_roles if r.id in
                         srv_sets['rolerules'][x.id]['requiresany']]

            if len(req_for_x) > 0 and set(req_for_x).isdisjoint(user.roles):
                unqualified_roles.append(x)

        self_roles = [r for r in self_roles if r not in unqualified_roles]

        if locked_out:
            self_roles = [r for r in self_roles if r not in conflicting_roles]

        if role not in self_roles:
            return await self.bot.say("You can't assign yourself that role.")

        conflicting_roles = unique(conflicting_roles)
        if len(conflicting_roles) > 0 and not locked_out:
            try:
                await self.bot.remove_roles(user, *conflicting_roles)
            except discord.Forbidden:
                return await self.bot.say("I don't seem to have the "
                                          "permissions required, contact "
                                          "a server admin to remedy this")
            except discord.HTTPException:
                return await self.bot.say("Something went wrong")

        try:
            await self.bot.add_roles(user, role)
        except discord.Forbidden:
            return await self.bot.say("I don't seem to have the "
                                      "permissions required, contact "
                                      "a server admin to remedy this")
        except discord.HTTPException:
            return await self.bot.say("Something went wrong")
        else:
            await self.bot.say("Role assigned.")
            if role in conflicting_roles:
                self.lockouts[server.id][user.id] = now


def unique(a):
    indices = sorted(range(len(a)), key=a.__getitem__)
    indices = set(next(it) for k, it in
                  itertools.groupby(indices, key=a.__getitem__))
    return [x for i, x in enumerate(a) if i in indices]


def check_folder():
    f = 'data/advroleassign'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/advroleassign/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = AdvRoleAssign(bot)
    bot.add_cog(n)
