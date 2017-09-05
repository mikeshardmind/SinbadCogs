import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import box, pagify
from .utils import checks
import itertools
import logging
import asyncio
from datetime import datetime, timedelta
assert timedelta  # Pyflakes, shut up; I'm using it implicitly

log = logging.getLogger('red.AdvRoleAssign')


class AdvRoleError(Exception):
    pass


class RoleSetting:

    def __init__(self, data=None):
        self.id = data.pop('id')
        self.exclusiveto = data.pop('exclusiveto')
        self.lockout = data.pop('lockoutoverride', None)
        self.requiresany = data.pop('requiresany': [])
        self.removable = data.pop('removable', False)

    def has_req(self, who: discord.Member):
        return not set(self.requiresany).isdisjoint([r.id for r in who.roles])

    def exclusive_overlap(self, who: discord.Member):
        return [r for r in who.roles if r.id in self.exclusiveto]

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
                                        'ignoredroles': [],
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
                self.rolerules[k] = []
            for l, b in v['rolerules'].items():
                data = {'exclusiveto': b.get('exclusiveto', None)
                        'requiresany': b.get('requiresany', None)
                        'lockoutoverride': b.get('lockoutoverride', None)
                        'id': l
                        'removable': b.get('removable', False)
                        }
                r = RoleSetting(**data)
                self.rolerules[k].append(r)

    def backwards_compatability(self):
        for k, v in self.settings.items():
            if v.get('version', None) is None:
                self.upgrade_v1_to_v2(k)
            if v.get('version') == 2:
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

    @advroleset.command(name="toggleremovable", no_pm=True, pass_context=True)
    async def toggleremovable(self, ctx, *roles: discord.Role):
        # REWRITE
        """
        takes a list of roles and toggles their removability
        default is that roles can not be self removed
        you can only set this for roles below yourself
        """
        server = ctx.message.server
        user = ctx.message.author
        self.initial_config(server)
        srv_sets = self.settings[server.id]

        if len(roles) == 0:
            return await self.bot.say("I need at least one role")

        valid_roles = [r for r in roles if r.id in srv_sets['selfroles']]

        if len(valid_roles) == 0:
            return await self.bot.say("None of those roles are self "
                                      "Assignable")

        if user != server.owner:
            valid_roles = [r for r in valid_roles if user.top_role >= r]

        if len(valid_roles) == 0:
            return await self.bot.say("All of those roles are above you, "
                                      "you can't change their settings")

        output = "List of edited roles and their removability:"
        for role in valid_roles:
            srv_sets['rolerules'][role.id]['removable'] = \
                not srv_sets['rolerules'][role.id].get('removable', False)
            output += "\n{0.name}: ".format(role)
            output += "{}".format(srv_sets['rolerules'][role.id]['removable'])

        if len(valid_roles) != len(roles):
            output += "\n\nThe following roles were unchanged as they were "
            output += "you: "
            roles = [r for r in roles if r not in valid_roles]
            for role in roles:
                output += "\n{0.name}".format(role)

        self.save_json()
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(box(page))

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
    async def advset_add_selfrole(self, ctx, *roles: discord.Role):
        """add role(s) that anyone can self assign"""

        server = ctx.message.server
        user = ctx.message.author

        if user != server.owner:
            to_add = [r for r in roles if user.top_role >= r]

            if len(to_add) == 0:
                return await self.bot.say("I could not add any of those roles."
                                          " All of them were above you ")

            elif len(to_add) != len(roles):
                await self.bot.say("One or more of those roles was not added."
                                   "Any unadded roles were above you.")
        else:
            to_add = roles
        self.initial_config(server)
        for role in roles:
            if role.id not in self.settings[server.id]['selfroles']:
                self.settings[server.id]['selfroles'].append(role.id)
        self.save_json()
        await asyncio.sleep(3)
        await self.bot.say("Finished adding roles.")

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
            self.settings[server.id]['rolerules'].pop(role.id, None)
            self.save_json()
            await self.bot.say("That role is no longer self assignable")
        else:
            await self.bot.say("That role was not self assignable")

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
        user = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        server_roles = server.roles
        now = datetime.utcnow()
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        if channel.id in srv_sets['silent']:
            try:
                await self.bot.delete_message(ctx.message)
            except Exception:
                pass
            return
        if not self._check_verified(server, user):
            return

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
            if x.id not in srv_sets['rolerules']:
                continue
            tst_exclusive = [r for r in server_roles if r.id in
                             srv_sets['rolerules'][x.id]['exclusiveto']]

            if not set(tst_exclusive).isdisjoint(user.roles):
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

    def _check_verified(self, server: discord.Server, member: discord.Member):
        """
        quick check to see if a member has been verified
        returns True if verification role has not been set
        """
        self.initial_config(server)
        srv_sets = self.settings[server.id]

        v_role = discord.utils.get(server.roles,
                                   id=srv_sets.get('verificationrole', "00"))
        if v_role is None:
            return True

        if srv_sets.get('strictverification', True):
            if v_role in member.roles:
                return True
            else:
                return False
        else:
            if member.top_role >= v_role:
                return True

        return False

    @advrole.command(name="remove", no_pm=True, pass_context=True)
    async def leaverole(self, ctx, role: discord.Role=None):
        """
        leaves a role if possible
        use without a role to see which of your roles you can remove
        """
        user = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        if channel.id in srv_sets['silent']:
            try:
                await self.bot.delete_message(ctx.message)
            except Exception:
                pass
        if not self._check_verified(server, user):
            return
        if not srv_sets['active']:
            if channel.id in srv_sets['silent']:
                return
            return await self.bot.say("Selfrole management is currently "
                                      "disabled.")

        removable_roles = [r for r in user.roles if r.id in
                           srv_sets['selfroles']]

        removable_roles = [r for r in removable_roles if
                           srv_sets['rolerules'][r.id].get('removable', False)]

        removable_roles = [r for r in removable_roles if
                           r < server.me.top_role]

        if role is None:
            if channel.id in srv_sets['silent']:
                return
            if len(removable_roles) == 0:
                return await self.bot.say("None of your roles are available "
                                          "for self removal")

            output = "The following roles are self removable:"
            for r in removable_roles:
                output += "\n{0.name}".format(r)

            for page in pagify(output, delims=["\n", ","]):
                await self.bot.say(box(page))

        elif role not in removable_roles:
            if channel.id in srv_sets['silent']:
                return
            return await self.bot.say("You can't remove that role. "
                                      "For a list of removable roles, use "
                                      "`{0.prefix}advrole remove` (without "
                                      "a role following it)".format(ctx))

        else:
            try:
                await self.bot.remove_roles(user, role)
            except discord.Forbidden:
                if channel.id in srv_sets['silent']:
                    return
                return await self.bot.say(self.permerror)
            except discord.HTTPException:
                if channel.id in srv_sets['silent']:
                    return
                return await self.bot.say("Something went wrong")
            else:
                if channel.id in srv_sets['silent']:
                    return
                await self.bot.say("Role removed")

    @advrole.command(name="join", no_pm=True, pass_context=True)
    async def joinrole(self, ctx, role: discord.Role):
        """joins a role which is available to you for self assignment"""
        user = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        server_roles = server.roles
        now = datetime.utcnow()
        self.initial_config(server)
        srv_sets = self.settings[server.id]
        if channel.id in srv_sets['silent']:
            try:
                await self.bot.delete_message(ctx.message)
            except Exception:
                pass
        if not self._check_verified(server, user):
            return
        ignoredroles = [r for r in server_roles
                        if r.id in srv_sets['ignoredroles']]
        locked_out = False
        conflicting_roles = []
        unqualified_roles = []

        if not srv_sets['active']:
            if channel.id in srv_sets['silent']:
                return
            return await self.bot.say("No roles currently self assignable.")

        if role in user.roles:
            if srv_sets.get('jointoremove', False):
                if role.id in srv_sets['selfroles']:
                    if srv_sets['rolerules'][role.id].get('removable', False):
                        try:
                            await self.bot.remove_roles(user, role)
                        except discord.Forbidden:
                            if channel.id in srv_sets['silent']:
                                return
                            return await self.bot.say(self.permerror)
                        except discord.HTTPException:
                            if channel.id in srv_sets['silent']:
                                return
                            return await self.bot.say("Something went wrong")
                        else:
                            if channel.id in srv_sets['silent']:
                                return
                            return await self.bot.say("Role removed")
                    else:
                        if channel.id in srv_sets['silent']:
                            return
                        return await self.bot.say("You can't remove that role")
                else:
                    if channel.id in srv_sets['silent']:
                        return
                    return await self.bot.say("You can't remove that role")
            else:
                if channel.id in srv_sets['silent']:
                    return
                return await self.bot.say("You already have that role.")

        if not set(ignoredroles).isdisjoint(user.roles):
            if channel.id in srv_sets['silent']:
                return
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
            if x == role and x.id in srv_sets['rolerules']:
                tst_exclusive = [r for r in server_roles if r.id in
                                 srv_sets['rolerules'][x.id]['exclusiveto']]
                rms = list(set(tst_exclusive).intersection(user.roles))
                conflicting_roles.append(rms)
            elif x in user.roles and role.id in srv_sets['rolerules']:
                tst_exclusive = [r for r in server_roles if r.id in
                                 srv_sets['rolerules'][role.id]['exclusiveto']]
                if x in tst_exclusive:
                    conflicting_roles.append(x)

            if x.id not in srv_sets['rolerules']:
                continue
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
                rms = [r for r in user.roles if r in conflicting_roles]
                await self.bot.remove_roles(user, *rms)
            except discord.Forbidden:
                if channel.id in srv_sets['silent']:
                    return
                return await self.bot.say(self.permerror)
            except discord.HTTPException:
                if channel.id in srv_sets['silent']:
                    return
                return await self.bot.say("Something went wrong")

        try:
            await self.bot.add_roles(user, role)
        except discord.Forbidden:
            if channel.id in srv_sets['silent']:
                return
            return await self.bot.say(self.permerror)
        except discord.HTTPException:
            if channel.id in srv_sets['silent']:
                return
            return await self.bot.say("Something went wrong")
        else:
            if role in conflicting_roles:
                self.lockouts[server.id][user.id] = now
            if channel.id in srv_sets['silent']:
                return
            await self.bot.say("Role assigned.")


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
