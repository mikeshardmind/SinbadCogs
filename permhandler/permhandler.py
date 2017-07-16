import os
import discord
import asyncio
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks
from cogs.utils.chat_formatting import box, pagify


class PermHandler:
    """
    Save myself time with managing an alliance discord
    """

    __author__ = "mikeshardmind"
    __version__ = "1.5"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/permhandler/settings.json')

    def save_json(self):
        dataIO.save_json("data/permhandler/settings.json", self.settings)

    @checks.admin_or_permissions(Manage_server=True)
    @commands.group(name="permhandle", aliases=["phandle"],
                    pass_context=True, no_pm=True)
    async def permhandle(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    def initial_config(self, server_id):
        """ensures the server has an entry"""

        if server_id not in self.settings:
            self.settings[server_id] = {'chans': [],
                                        'roles': [],
                                        'activated': False,
                                        'proles': []
                                        }
        if 'chans' not in self.settings[server_id]:
            self.settings[server_id]['chans'] = []
        if 'roles' not in self.settings[server_id]:
            self.settings[server_id]['roles'] = []
        if 'activated' not in self.settings[server_id]:
            self.settings[server_id]['chans'] = False
        if 'proles' not in self.settings[server_id]:
            self.settings[server_id]['proles'] = []
        if 'floor' not in self.settings[server_id]:
            self.settings[server_id]['floor'] = None
        self.save_json()

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="newrole", pass_context=True, no_pm=True)
    async def make_role(self, ctx, *, name):
        """makes a new role and adds it to the priveleged role list"""
        rname = str(name)
        if not all(x.isalpha() or x.isspace() for x in rname):
            return await self.bot.say("Guild names must be made "
                                      "of letters and spaces")
        server = ctx.message.server

        r = await self.bot.create_role(server, name=rname, hoist=True,
                                       mentionable=True)
        self.settings[server.id]['roles'].append(r.id)
        self.save_json()
        await self.validate(server)
        await self.reorder_roles(server)
        await self.bot.say("Guild role made and configured")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="roleinfo", pass_context=True, no_pm=True)
    async def r_info(self, ctx, *, role):
        """get info about a role by name or ID"""
        nameID = str(role).strip().lower()
        rn = [r for r in ctx.message.server.roles
              if r.name.strip().lower() == nameID or r.id == nameID]
        if rn:
            if len(rn) == 1:
                return await self.bot.say("Role name: `{}`\nRole ID: `{}`"
                                          "".format(rn[0].name, rn[0].id))
        await self.bot.say("There was not a unique exact match.")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="configdump", pass_context=True,
                        no_pm=True, hidden=True)
    async def configdump(self, ctx):
        """lists current config info"""
        server = ctx.message.server
        self.initial_config(server.id)
        chans = self.settings[server.id]['chans']
        channels = server.channels
        channels = [c for c in channels if c.id in chans]
        roles = self.settings[server.id]['roles']
        proles = self.settings[server.id]['proles']
        role_list = server.roles
        prole_list = server.roles
        rls = [r.name for r in role_list if r.id in roles]
        pcs = [r.name for r in prole_list if r.id in proles]
        vcs = [c.name for c in channels if c.type == discord.ChannelType.voice]
        tcs = [c.name for c in channels if c.type == discord.ChannelType.text]
        floor_role = [r.name for r in role_list
                      if r.id == self.settings[server.id]['floor']]

        output = ""
        output += "Priveleged Roles: {}".format(rls)
        output += "\nProtected Roles: {}".format(pcs)
        output += "\nProtected Voice Chats: {}".format(vcs)
        output += "\nProtected Text Chats: {}".format(tcs)
        output += "\nFloor Role: {}".format(floor_role)
        for page in pagify(output, delims=["\n", ","]):
            await self.bot.send_message(ctx.message.author, box(page))

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="roledump", pass_context=True, no_pm=True)
    async def roledump(self, ctx):
        """ lists roles and their IDs"""
        server = ctx.message.server
        role_list = server.roles

        output = ""
        for r in role_list:
            output += "\n{} : {}".format(r.name, r.id)
        for page in pagify(output, delims=["\n"]):
            await self.bot.send_message(ctx.message.author, box(page))

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="toggleactive", pass_context=True, no_pm=True)
    async def toggleactive(self, ctx):
        """Does what it says """
        server = ctx.message.server
        self.initial_config(server.id)
        self.settings[server.id]['activated'] = \
            not self.settings[server.id]['activated']
        self.save_json()
        await self.validate(server)
        await self.bot.say(
            "Active: {}".format(self.settings[server.id]['activated']))

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="addrole", pass_context=True, no_pm=True)
    async def addrole(self, ctx, role_id: str):
        """add a priveleged role"""
        server = ctx.message.server
        self.initial_config(server.id)
        r = [r for r in server.roles if r.id == role_id]
        if not r:
            return await self.bot.say("No such role")
        if role_id in self.settings[server.id]['roles']:
            return await self.bot.say("Already in roles")
        self.settings[server.id]['roles'].append(role_id)
        self.save_json()
        await self.validate(server)
        await self.reorder_roles(server)
        await self.bot.say("Role added.")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="addprole", pass_context=True, no_pm=True)
    async def addprole(self, ctx, role_id: str):
            """add role that can only be held by users with priveleged roles"""
            server = ctx.message.server
            self.initial_config(server.id)
            r = [r for r in server.roles if r.id == role_id]
            if not r:
                return await self.bot.say("No such role")
            if role_id in self.settings[server.id]['proles']:
                return await self.bot.say("Already in roles")
            self.settings[server.id]['proles'].append(role_id)
            self.save_json()
            await self.validate(server)
            await self.bot.say("Role added.")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="remrole", pass_context=True, no_pm=True)
    async def remrole(self, ctx, role_id: str):
        """remove a priveleged role"""
        server = ctx.message.server
        self.initial_config(server.id)
        r = [r for r in server.roles if r.id == role_id][0]
        if not r:
            return await self.bot.say("No such role")
        if role_id not in self.settings[server.id]['roles']:
            return await self.bot.say("Not in roles")
        self.settings[server.id]['roles'].remove(role_id)
        self.save_json()
        await self.validate(server)
        await self.bot.say("Role removed.")
        if self.settings[server.id]['floor'] is not None:
            if server.me.top_role > r:
                await self.bot.move_role(server, r, 1)

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="remprole", pass_context=True, no_pm=True)
    async def remprole(self, ctx, role_id: str):
        """remove a protected role"""
        server = ctx.message.server
        self.initial_config(server.id)
        r = [r for r in server.roles if r.id == role_id]
        if not r:
            return await self.bot.say("No such role")
        if role_id not in self.settings[server.id]['proles']:
            return await self.bot.say("Not in roles")
        self.settings[server.id]['proles'].remove(role_id)
        self.save_json()
        await self.validate(server)
        await self.bot.say("Role removed.")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="addchan", pass_context=True, no_pm=True)
    async def addchan(self, ctx, chan_id: str):
        """add a restricted channel"""
        server = ctx.message.server
        self.initial_config(server.id)
        c = [c for c in server.channels if c.id == chan_id]
        if not c:
            return await self.bot.say("No such channel")
        if chan_id in self.settings[server.id]['chans']:
            return await self.bot.say("Already in channels")
        self.settings[server.id]['chans'].append(chan_id)
        self.save_json()
        await self.validate(server)
        await self.bot.say("Channel added.")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="remchan", pass_context=True, no_pm=True)
    async def remchan(self, ctx, chan_id: str):
        """remove a restricted channel"""
        server = ctx.message.server
        self.initial_config(server.id)
        c = [c for c in server.channels if c.id == chan_id]
        if not c:
            return await self.bot.say("No such role")
        if chan_id not in self.settings[server.id]['chans']:
            return await self.bot.say("Not in channels")
        self.settings[server.id]['chans'].remove(chan_id)
        self.save_json()
        await self.validate(server)
        await self.bot.say("Channel removed")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="setfloor", pass_context=True, no_pm=True)
    async def set_floor(self, ctx, role_id: str):
        """sets the role all protected and priveleged roles should be above"""
        server = ctx.message.server
        self.initial_config(server.id)
        r = [r for r in server.roles if r.id == role_id][0]
        if not r:
            return await self.bot.say("No such role")
        self.settings[server.id]['floor'] = r.id
        self.save_json()
        await self.bot.say("Floor set, I will now validate settings.")
        await self.validate(server)
        await self.bot.say("Settings validated: you are good to go.")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="validate", pass_context=True, no_pm=True)
    async def manual_validate(self, ctx):
        """manually revalidate everything"""
        await self.validate(ctx.message.server)
        await self.reorder_roles(ctx.message.server)
        await self.bot.say("Permissions Verified")

    @checks.admin_or_permissions(Manage_server=True)
    @permhandle.command(name="audit", pass_context=True,
                        no_pm=True, hidden=True)
    async def manual_audit(self, ctx):
        await self.validate(ctx.message.server)
        await self.bot.say("Permissions Verified")
        await self.bot.say("this next step will take a while...")
        await self.audit(ctx.message.server)
        await self.reorder_roles(ctx.message.server)
        await self.bot.say("Audit complete.")

    async def validate(self, server):
        if not self.settings[server.id]['activated']:
            return

        chans = self.settings[server.id]['chans']
        channels = server.channels
        channels = [c for c in channels if c.id in chans]
        roles = self.settings[server.id]['roles']
        proles = self.settings[server.id]['proles']

        role_list = [r for r in server.roles if r.id in roles]
        prole_list = [r for r in server.roles if r.id in proles]
        vchans = [c for c in channels if c.type == discord.ChannelType.voice]
        tchans = [c for c in channels if c.type == discord.ChannelType.text]

        for vchan in vchans:
            e_overwrites = vchan.overwrites
            e_roles = [e[0] for e in e_overwrites]
            for e_role in e_roles:
                if e_role not in role_list:
                    overwrite = discord.PermissionOverwrite()
                    overwrite.connect = None
                    await self.bot.edit_channel_permissions(vchan, e_role,
                                                            overwrite)
                    await asyncio.sleep(1)

            for role in role_list:
                overwrite = discord.PermissionOverwrite()
                overwrite.connect = True
                await self.bot.edit_channel_permissions(vchan, role,
                                                        overwrite)
                await asyncio.sleep(1)

        for tchan in tchans:
            e_overwrites = tchan.overwrites
            e_roles = [e[0] for e in e_overwrites]
            for e_role in e_roles:
                if e_role not in role_list:
                    overwrite = discord.PermissionOverwrite()
                    overwrite.read_messages = None
                    await self.bot.edit_channel_permissions(tchan, e_role,
                                                            overwrite)
                    await asyncio.sleep(1)

            for role in role_list:
                overwrite = discord.PermissionOverwrite()
                overwrite.read_messages = True
                await self.bot.edit_channel_permissions(tchan, role,
                                                        overwrite)
                await asyncio.sleep(1)

    async def audit(self, server):
        if not self.settings[server.id]['activated']:
            return
        await self.validate(server)
        roles = self.settings[server.id]['roles']
        role_list = [r for r in server.roles if r.id in roles]
        proles = self.settings[server.id]['proles']
        await self.bot.request_offline_members(server)
        members = list(server.members)

        for member in members:
            if set(role_list).isdisjoint(member.roles):
                rms = [r for r in member.roles if r.id in proles]
                await self.bot.remove_roles(member, *rms)
                await asyncio.sleep(1)

    async def reorder_roles(self, server):
        if self.settings[server.id]['floor'] is None:
            return
        roles = self.settings[server.id]['roles']
        role_list = [r for r in server.roles if r.id in roles]
        floor_role = [r for r in server.roles
                      if r.id == self.settings[server.id]['floor']][0]
        bot_top_role = server.me.top_role
        f_position = floor_role.position
        for role in role_list:
            await asyncio.sleep(1)
            if role < floor_role:
                if floor_role < bot_top_role:
                    await self.bot.move_role(server, role, floor_role.position)


def check_folder():
    f = 'data/permhandler'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/permhandler/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = PermHandler(bot)
    bot.add_cog(n)
