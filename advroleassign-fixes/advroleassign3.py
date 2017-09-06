import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import box, pagify
from .utils import checks
import itertools
import logging
import asyncio
from typing import Union
from datetime import datetime, timedelta
assert timedelta  # Pyflakes, shut up; I'm using it implicitly

log = logging.getLogger('red.AdvRoleAssign')


class AdvRoleError(Exception):
    pass


class RoleSetting:

    def __init__(self, data=None):
        self.id = data.pop('id')
        self.exclusiveto = data.pop('exclusiveto', [])
        self.lockoutoverride = data.pop('lockoutoverride', False)
        self.requiresany = data.pop('requiresany', [])
        self.removable = data.pop('removable', False)

    def has_req(self, who: discord.Member):
        return not set(self.requiresany).isdisjoint([r.id for r in who.roles])

    def exclusive_overlap(self, who: discord.Member):
        return [r for r in who.roles if r.id in self.exclusiveto]

    def update(self, changed=None):
        self.exclusiveto = changed.pop('exclusiveto', self.exclusiveto)
        self.lockoutoverride = changed.pop('lockoutoverride',
                                           self.lockoutoverride)
        self.requiresany = changed.pop('requiresany': self.requiresany)
        self.removable = changed.pop('removable', self.removable)

    def to_dict(self):
        data = {'id': self.id,
                'exclusiveto': self.exclusiveto,
                'lockoutoverride': self.lockout,
                'requiresany': self.requiresany,
                'removable': self.removable
                }
        return data


class AdvRoleAssign:

    """
    Tool for setting up mutually exclusive self-assignable roles
    with optional lockout
    """
    __author__ = "mikeshardmind"
    __version__ = "3.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/advroleassign/settings.json')
        self.lockouts = {}
        self.rolerules = {}
        self._graceful_load()

    def save_json(self):
        dataIO.save_json('data/advroleassign/settings.json', self.settings)

    def initial_config(self, server):
        if server.id not in self.settings:
            self.settings[server.id] = {'selfroles': [],
                                        'active': False,
                                        'lockout': 0,
                                        'rolerules': {},
                                        'ignored': [],
                                        'version': 3
                                        }
        if 'silent' not in self.settings[server.id]:
            self.settings[server.id].update({'silent': []})
        if self.settings[server.id].get('version', None) != 2:
            self.backwards_compatability()
        self.save_json()

    def _graceful_load(self):
        self.backwards_compatability()
        self.save_json()
        for k, v in self.settings.items():
            if k not in self.rolerules:
                self.rolerules[k] = {}
            for l, b in v['rolerules'].items():
                data = {'exclusiveto': b.get('exclusiveto', None)
                        'requiresany': b.get('requiresany', None)
                        'lockoutoverride': b.get('lockoutoverride', False)
                        'id': l
                        'removable': b.get('removable', False)
                        }
                r = RoleSetting(data)
                self.rolerules[k][l] = r

    def backwards_compatability(self):
        for k, v in self.settings.items():
            if v.get('version', None) is None:
                self.upgrade_v1_to_v2(k)
            if v.get('version') == 2:
                self.upgrade_v2_to_v3(k)

    def upgrade_v2_to_v3(self, server_id):
        srv_sets = self.settings[server_id]
        srv_sets['ignored'] = srv_sets.pop('ignoredroles', [])
        srv_sets.update({'version': 3})

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

    @advroleset.group(name="verify", no_pm=True, pass_context=True)
    async def verify(self, ctx):
        """settings for server verification roles"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @verify.command(name="role", no_pm=True, pass_context=True)
    async def setverificationrole(self, ctx, role: discord.Role=None):
        """
        set the verification role, call without parameters to clear setting
        """
        server = ctx.message.server
        self.initial_config(server)
        srv_sets = self.settings[server.id]

        rid = role.id if role is not None else None
        srv_sets.update({'verificationrole': rid})
        self.save_json()
        if role is not None:
            await self.bot.say("Verification role: {0.name}".format(role))
        else:
            await self.bot.say("Verification role cleared")

    @verify.command(name="togglestrict", no_pm=True, pass_context=True)
    async def strictverificationtoggle(self, ctx):
        """
        toggles strict mode for verification. Defaults to strict.
        Wehn toggled off, any role above the verification role works
        """
        server = ctx.message.server
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        srv_sets['strictverification'] = \
            not srv_sets.get('strictverification', True)
        self.save_json()
        if srv_sets['strictverification']:
            await self.bot.say("Strict mode enabled")
        else:
            await self.bot.say("Strict mode disabled")

    @advroleset.command(name="silentchannels", no_pm=True, pass_context=True)
    async def set_silent_channels(self, ctx, *channels: discord.Channel):
        """
        takes a list of channels and sets them to silent. non admin commands
        that issue feedback only will not work in silent channels
        non admin commands that do things,
        will do them silently in silent channels
        Use with no arguments to clear the list of silent channels
        """

        server = ctx.message.server
        self.initial_config(server)
        self.settings[server.id]['silent'] = \
            [c.id for c in channels if c in server.channels]

        if len(self.settings[server.id]['silent']) == 0:
            await self.bot.say("Silent channel list cleared")
        else:
            await self.bot.say("Silent channels set")

    @advroleset.command(name="viewconfig", no_pm=True, pass_context=True)
    async def viewconfig(self, ctx):
        # REWRITE?
        """sends you info on the current config"""
        server = ctx.message.server
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        output = ""

        output += "Enabled: {}".format(srv_sets['active'])
        v_id = srv_sets.get('verificationrole', "00")
        v_role = discord.utils.get(server.roles, id=v_id)
        if v_role is not None:
            output += "\nVerification Role: {0.name}".format(v_role)
            output += "\nStrict Verification: {}" \
                      "".format(srv_sets.get('strictverification', True))

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

                output += \
                    "\nIs removable: {}" \
                    "".format(srv_sets['rolerules'][role.id].get('removable',
                                                                 False))

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

    @advroleset.command(name="togglejoinremove", no_pm=True, pass_context=True)
    async def togglejoinremove(self, ctx):
        """
        toggles the default behavior of trying to join a role you
        own already. Default is to tell you you own, toggles to
        attempting to remove it if removable
        """
        server = ctx.message.server
        self.initial_config(server)
        srv_sets = self.settings[server.id]

        srv_sets['jointoremove'] = not srv_sets.get('jointoremove', False)
        self.save_json()
        if srv_sets['jointoremove']:
            await self.bot.say("Join now doubles as removal command")
        else:
            await self.bot.say("Join no longer doubles as removal command")

    @advroleset.command(name="setremovable", no_pm=True, pass_context=True)
    async def setremovable(self, ctx, *roles: discord.Role):
        """
        takes a list of roles and sets them as self removable
        default is that roles can not be self removed
        you can only set this for roles below yourself
        """
        server = ctx.message.server
        user = ctx.message.author
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        roles = [r for r in roles if r.id in srv_sets['selfroles']]
        if len(roles) == 0:
            return await self.bot.say("None of those are valid self roles")
        output = ""
        for role in self.advroleset_filter(roles, yld=True):
            self.add_or_update_role(role, {'removable': True})
            output += "\n{0.name}".format(role)
        if output == "":
            return await self.bot.say("You can't change any of those roles")
        output = "The following roles have been set as self-removable: \n" \
                 + output
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(box(page))

    @advroleset.command(name="setnonremovable", no_pm=True, pass_context=True)
    async def setunremovable(self, ctx, *roles: discord.Role):
        """
        takes a list of roles and sets them as non-self-removable
        default is that roles can not be self removed
        you can only set this for roles below yourself
        """
        server = ctx.message.server
        user = ctx.message.author
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        roles = [r for r in roles if r.id in srv_sets['selfroles']]
        if len(roles) == 0:
            return await self.bot.say("None of those are valid self roles")
        output = ""
        for role in self.advroleset_filter(roles, yld=True):
            self.add_or_update_role(role, {'removable': False})
            output += "\n{0.name}".format(role)
        if output == "":
            return await self.bot.say("You can't change any of those roles")
        output = "The following roles have been set as non-removable: \n" \
                 + output
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(box(page))

    @advroleset.command(name="ignore", pass_context=True, no_pm=True)
    async def ignorerole(self, ctx, *ignore: Union[discord.Role,
                                                   discord.Member]):
        """
        Ignore a list of users and/or roles
        """
        server = ctx.message.server
        author = ctx.message.author
        self.initial_config(server)
        if self.is_ignored(author):
            return
        ignore = unique(ignore)
        if len(ignore) == 0:
            return await self.bot.send_cmd_help(ctx)
        ignore = [i for i in ignore if not self.is_ignored(i)]
        if len(ignore) == 0:
            return await self.bot.say("I was already ignoring all of them")
        ignore = self.advroleset_filter(ignore)
        if len(ignore) == 0:
            return await self.bot.say("You can't have me ignore people higher "
                                      "than you in the heirarchy")
        self.settings[server.id]['ignored'].extend([i.id for i in ignore])
        self.save_json()

    @advroleset.command(name="unignore", pass_context=True, no_pm=True)
    async def unignorerole(self, ctx, unignore: Union[discord.Role,
                                                      discord.Member]):
        """
        unignore a list of users and/or roles
        """
        server = ctx.message.server
        author = ctx.message.author
        self.initial_config(server)
        if self.is_ignored(author):
            return
        unignore = unique(unignore)
        if len(unignore) == 0:
            return await self.bot.send_cmd_help(ctx)
        unignore = [i for i in unignore if self.is_ignored(i)]
        if len(unignore) == 0:
            return await self.bot.say("I wasn't ignoring any of them")
        unignore = self.advroleset_filter(unignore)
        if len(unignore) == 0:
            return await self.bot.say("You can't have me unignore people "
                                      "higher than you in the heirarchy")
        self.settings[server.id]['ignored'] = \
            [i for i in self.settings[server.id]['ignored']
             if i.id not in unignore]
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

    @advroleset.command(name="addselfroles", no_pm=True, pass_context=True)
    async def advset_add_selfrole(self, ctx, *roles: discord.Role):
        """add role(s) for self assignment"""
        server = ctx.message.server
        author = ctx.message.author
        self.initial_config(server)
        if self.is_ignored(author):
            return
        if len(roles) == 0:
            return await self.bot.send_cmd_help(ctx)
        roles = [r for r in roles
                 if r.id not in self.settings[server.id]['selfroles']]
        if len(roles) == 0:
            return await self.bot.say("Those are all already self roles")
        output = ""
        for role in self.advroleset_filter(roles, yld=True):
            self.add_or_update_role(role)
            output += "\n{0.name}".format(role)
        if output == "":
            return await self.bot.say("You can't give away roles higher than "
                                      "you are in the heirarchy")
        output = "The following roles have been set as self assignable: \n" \
                 + output
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(box(page))

    @advroleset.command(name="requirerole", no_pm=True, pass_context=True)
    async def advset_requireroles(self, ctx, role: discord.Role,
                                  *roles: discord.Role):
        """
        Takes a list of roles. The first role is the role to restrict.
        Every role after it is a role that allows you to assign the first role
        call with only a single role to clear the requirement.
        """

    @advroleset.command(name="mutuallyexclusive",
                        no_pm=True, pass_context=True)
    async def advset_mutualexclusive(self, ctx, *roles: discord.Role):
        """
        Designate a list of roles which are mutually exclusive to eachother
        if called with only a single role, instead clears any mutual
        exclusivity settings for that role
        """

    @advroleset.command(name="delselfrole", no_pm=True, pass_context=True)
    async def advset_rem_selfrole(self, ctx, roles: discord.Role):
        """remove role(s) from the self assignable list"""
        server = ctx.message.server
        author = ctx.message.author
        self.initial_config(server)
        if self.is_ignored(author):
            return
        if len(roles) == 0:
            return await self.bot.send_cmd_help(ctx)
        roles = [r for r in roles
                 if r.id in self.settings[server.id]['selfroles']]
        if len(roles) == 0:
            return await self.bot.say("None of those are self assignable")
        output = ""
        for role in self.advroleset_filter(roles, yld=True):
            self.add_or_update_role(role)
            output += "\n{0.name}".format(role)
        if output == "":
            return await self.bot.say("You can't modify roles higher than "
                                      "you are in the heirarchy")
        output = "The following roles have been removed from being " \
                 "self assignable: \n" + output
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(box(page))

    @commands.group(name="advrole", no_pm=True, pass_context=True)
    async def advrole(self, ctx):
        """commands for self assigning roles"""
        if ctx.invoked_subcommand is None:
            server = ctx.message.server
            channel = ctx.message.channel
            self.initial_config(server)
            srv_sets = self.settings[server.id]
            if channel.id in srv_sets['silent']:
                try:
                    await self.bot.delete_message(ctx.message)
                except Exception:
                    pass
                return
            await self.bot.send_cmd_help(ctx)

    @advrole.command(name="list", no_pm=True, pass_context=True)
    async def listroles(self, ctx):
        """list roles which are available to you for self assignment"""

    @advrole.command(name="remove", no_pm=True, pass_context=True)
    async def leaverole(self, ctx, role: discord.Role=None):
        """
        leaves a role if possible
        use without a role to see which of your roles you can remove
        """

    @advrole.command(name="join", no_pm=True, pass_context=True)
    async def joinrole(self, ctx, role: discord.Role):
        """joins a role which is available to you for self assignment"""

    def advroleset_filter(self, who: discord.Member,
                          *flist: Union[discord.Role, discord.Member],
                          **kwargs):
        server = who.server
        flist = unique(flist)
        if not server.permissions_for(who).administrator:
            roles = [r for r in flist if isinstance(r, discord.Role)]
            users = [u for u in flist if u not in roles]
            users = [u for u in users if u.top_role < who.top_role]
            roles = [r for r in roles if r < who.top_role]
            returnlist = users + roles
        if kwargs.pop('yld', False):
            for ret in returnlist:
                yield ret
        else:
            return returnlist

    def get_joinable(self, who: discord.Member, **kwargs):
        server = who.server
        sid = server.id
        roles = [r for r in server.roles
                 if r.id in self.settings[sid]['selfroles']
                 and r not in who.roles]
        roles = [r for r in roles if not
                 set(self.rolerules[sid][r.id]['requiresany']).isdisjoint(
                                                [x.id for x in who.roles])]
        if kwargs.pop('yld', False):
            for role in roles:
                yield role
        else:
            return roles

    def add_or_update_role(self, role: discord.Role, data):
        if role.id not in self.settings[role.server.id]['selfroles']:
            self.settings[role.server.id]['selfroles'].append(role.id)
        if role.id not in self.rolerules[role.server.id]:
            r = RoleSetting(data)
            self.rolerules[role.server.id][role.id] = r
        else:
            self.rolerules[role.server.id][role.id].update(data)
        self.settings[role.server.id]['rolerules'][role.id] = \
            self.rolerules[role.server.id][role.id].to_dict()
        self.save_json()

    def is_ignored(self, who: Union[discord.Member, discord.Role]):
        if who.id in self.settings[who.server.id]['ignored']:
            return True
        if isinstance(who, discord.Member):
            for role in who.roles:
                if self.is_blacklisted(role):
                    return True
            return False


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
