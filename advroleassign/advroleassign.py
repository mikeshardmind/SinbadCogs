import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import box, pagify
from .utils import checks
from datetime import datetime, timedelta
assert timedelta  # Pyflakes, shut up; I'm using it implicitly


class AdvRoleAssign:

    """
    Tool for setting up mutually exclusive self-assignable roles
    with optional lockout
    """
    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/advroleassign/settings.json')
        self.lockouts = {}

    def save_json(self):
        dataIO.save_json('data/advroleassign/settings.json', self.settings)

    def initial_config(self, server_id):
        if server_id not in self.settings:
            self.settings[server_id] = {'selfroles': [],
                                        'membershiproles': [],
                                        'memberselfroles': [],
                                        'active': False,
                                        'exclusiveroles': [],
                                        'lockout': 0
                                        }
            self.save_json()

    @checks.mod_or_permissions(manage_roles=True)
    @commands.group(name="advroleset", no_pm=True, pass_context=True)
    async def advroleset(self, ctx):
        """settings for advroleassign"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @advroleset.command(name="toggleactive", no_pm=True, pass_context=True)
    async def toggle_active(self, ctx):
        """
        toggles the ability for users to assign roles
        """
        server = ctx.message.server
        if server not in self.settings:
            self.initial_config(server.id)
        self.settings[server.id]['active'] = \
            not self.settings[server.id]['active']
        self.save_json()

        if self.settings[server.id]['active']:
            await self.bot.say("Activated.")
        else:
            await self.bot.say("Deactivated.")

    @advroleset.command(name="setlockout", no_pm=True, pass_context=True)
    async def set_lockout(self, ctx, seconds: int):
        """
        sets the minimum amount of time inbetween switching from one exclusive
        role to another
        """

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        self.settings[server.id]['lockout'] = seconds
        self.save_json()

        await self.bot.say("Lockout on switching between exclusive roles "
                           "is set to {} second(s)".format(seconds))

    @advroleset.command(name="addselfrole", no_pm=True, pass_context=True)
    async def advset_add_selfrole(self, ctx, role: discord.Role):
        """add a role that anyone can self assign"""

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if role.id not in self.settings[server.id]['selfroles']:
            self.settings[server.id]['selfroles'].append(role.id)
            self.save_json()
            await self.bot.say("Role added to self assignable list")
        else:
            await self.bot.say("That role is already self assignable")

    @advroleset.command(name="addmembselfrole", no_pm=True, pass_context=True)
    async def advset_add_memberselfrole(self, ctx, role: discord.Role):
        """
        add a role that people who have one or more of another
        configureable role can self assign
        """

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if role.id not in self.settings[server.id]['memberselfroles']:
            self.settings[server.id]['memberselfroles'].append(role.id)
            await self.bot.say("Role added to self assignable list")
        else:
            await self.bot.say("That role is already self assignable")

    @advroleset.command(name="addreqrole", no_pm=True, pass_context=True)
    async def advset_add_membershiprole(self, ctx, role: discord.Role):
        """Designate a role which is required to self assign certain roles"""

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if role.id not in self.settings[server.id]['membershiproles']:
            self.settings[server.id]['membershiproles'].append(role.id)
            self.save_json()
            await self.bot.say("Role added to list")
        else:
            await self.bot.say("That role is already listed")

    @advroleset.command(name="addexclusiverole", no_pm=True, pass_context=True)
    async def advset_add_mexclusiverole(self, ctx, role: discord.Role):
        """
        sets a role as mutually exclusive from others in this list
        this is only checked when a role is obtained through this cog's
        commands
        """

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        if role.id not in self.settings[server.id]['exclusiveroles']:
            self.settings[server.id]['exclusiveroles'].append(role.id)
            self.save_json()
            await self.bot.say("Role added to list")
        else:
            await self.bot.say("That role is already listed")

    @advroleset.command(name="delselfrole", no_pm=True, pass_context=True)
    async def advset_rem_selfrole(self, ctx, role: discord.Role):
        """remove a role from the self assignable list"""

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        try:
            self.settings[server.id]['selfroles'].remove(role.id)
            self.save_json()
        except ValueError:
            await self.bot.say("That role was not self assignable")
        else:
            await self.bot.say("That role is no longer self assignable")

    @advroleset.command(name="delmembselfrole", no_pm=True, pass_context=True)
    async def advset_rem_memberselfrole(self, ctx, role: discord.Role):
        """remove a role from the restricted selfrole list"""

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        try:
            self.settings[server.id]['memberselfroles'].remove(role.id)
            self.save_json()
        except ValueError:
            await self.bot.say("That role was not self assignable")
        else:
            await self.bot.say("That role is no longer self assignable")

    @advroleset.command(name="delreqrole", no_pm=True, pass_context=True)
    async def advset_rem_membershiprole(self, ctx, role: discord.Role):
        """
        remove a role from the list of roles allowed to self assignable
        restricted roles
        """
        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        try:
            self.settings[server.id]['membershiproles'].remove(role.id)
            self.save_json()
        except ValueError:
            await self.bot.say("That role was not in the list")
        else:
            await self.bot.say("That role has been removed from the list")

    @advroleset.command(name="delexclusiverole", no_pm=True, pass_context=True)
    async def advset_rem_mexclusiverole(self, ctx, role: discord.Role):
        """remove a role from the list of roles which are mutually exclusive"""

        server = ctx.message.server
        if server.id not in self.settings:
            self.initial_config(server.id)
        try:
            self.settings[server.id]['exclusiveroles'].remove(role.id)
            self.save_json()
        except ValueError:
            await self.bot.say("That role was not in the list")
        else:
            await self.bot.say("That role has been removed from the list")

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
        if server.id not in self.settings:
            self.initial_config(server.id)
        if not self.settings[server.id]['active']:
            return await self.bot.say("No roles currently self assignable.")

        mlist = self.settings[server.id]['membershiproles']
        membership_roles = [r for r in server_roles if r.id in mlist]
        selfrolelist = self.settings[server.id]['selfroles']
        self_roles = [r for r in server_roles if r.id in selfrolelist]
        mslist = self.settings[server.id]['memberselfroles']
        member_roles = [r for r in server_roles if r.id in mslist]
        elist = self.settings[server.id]['exclusiveroles']
        exclusive_roles = [r for r in server_roles if r.id in elist]

        if not set(membership_roles).isdisjoint(user.roles):
            self_roles.extend(member_roles)

        if len(self_roles) == 0:
            return await self.bot.say("There are no self assignable roles "
                                      "available to you")

        output = "The following roles are available to you:\n"

        for role in self_roles:
            if role not in user.roles:
                output += "\n{}".format(role.name)

        exclusive_roles = [r for r in exclusive_roles if r in self_roles]

        if not set(exclusive_roles).isdisjoint(user.roles) \
                and len(exclusive_roles) > 1:
            owned = list(set(exclusive_roles).intersection(user.roles))[0]
            output += "\n\nWarning: You currently hold the role: {}\n" \
                      "If you try to assign any of the following roles, " \
                      "you will lose access to this role as it is " \
                      "mutually exclusive from them:\n".format(owned.name)

            exclusive_roles = [r for r in exclusive_roles if r != owned]

            for role in exclusive_roles:
                output += "\n{}".format(role.name)

        for page in pagify(output, delims=["\n", ","]):
            await self.bot.send_message(ctx.message.channel, box(page))

    @advrole.command(name="join", no_pm=True, pass_context=True)
    async def joinrole(self, ctx, role: discord.Role):
        """joins a role which is available to you for self assignment"""
        user = ctx.message.author
        server = ctx.message.server
        server_roles = server.roles
        now = datetime.utcnow()

        if server.id not in self.settings:
            self.initial_config(server.id)
        if not self.settings[server.id]['active']:
            return await self.bot.say("Role self assignment is disabled")

        mlist = self.settings[server.id]['membershiproles']
        membership_roles = [r for r in server_roles if r.id in mlist]
        selfrolelist = self.settings[server.id]['selfroles']
        self_roles = [r for r in server_roles if r.id in selfrolelist]
        mslist = self.settings[server.id]['memberselfroles']
        member_roles = [r for r in server_roles if r.id in mslist]
        elist = self.settings[server.id]['exclusiveroles']
        exclusive_roles = [r for r in server_roles if r.id in elist]

        if not set(membership_roles).isdisjoint(user.roles):
            self_roles.extend(member_roles)

        if role in user.roles:
            return await self.bot.say("You already have that role.")

        if role not in self_roles:
            return await self.bot.say("You can't assign yourself that role.")

        if role in exclusive_roles:
            if server.id not in self.lockouts:
                self.lockouts[server.id] = {}
            if user.id in self.lockouts[server.id]:
                tdelta = now - self.lockouts[server.id][user.id]
                if tdelta.seconds < self.settings[server.id]['lockout']:
                    return await self.bot.say("You can't switch to that role "
                                              "right now; you assigned a "
                                              "role mutually exclusive to it "
                                              "too recently. You can switch "
                                              "again in {} seconds"
                                              "".format((self.settings[server.id]['lockout'] - tdelta.seconds)))

            owned = list(set(exclusive_roles).intersection(user.roles))
            if len(owned) > 0:
                try:
                    await self.bot.remove_roles(user, *owned)
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
            if role in exclusive_roles:
                self.lockouts[server.id][user.id] = now


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
