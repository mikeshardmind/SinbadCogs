from typing import AsyncIterator, Tuple
from abc import ABC

import discord
from redbot.core import checks, commands, bank
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify

from .utils import UtilMixin
from .massmanager import MassManagementMixin
from .events import EventMixin

# from .notifications import NotificationMixin
from .exceptions import RoleManagementException, PermissionOrHierarchyException


class Meta(type(commands.Cog), type(ABC)):
    """ Fricking mypy + discord.py use of classes and a base metaclass """

    pass


class RoleManagement(
    UtilMixin, MassManagementMixin, EventMixin, commands.Cog, metaclass=Meta
):
    """
    Cog for role management
    """

    __author__ = "mikeshardmind (Sinbad)"
    __version__ = "4.0.0"
    __flavor_text__ = "Major Breakage: Red 3.1 Support"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_role(
            exclusive_to=[],
            requires_any=[],
            requires_all=[],
            sticky=False,
            self_removable=False,
            self_role=False,
            protected=False,
            cost=0,
        )
        self.config.register_member(roles=[], forbidden=[])
        self.config.init_custom("REACTROLE", 2)
        self.config.register_custom(
            "REACTROLE", roleid=None, channelid=None, guildid=None
        )  # ID : Message.id, str(React)
        self.config.register_guild(notify_channel=None)
        super().__init__()

    async def cog_before_invoke(self, ctx):
        if ctx.guild:
            await self.maybe_update_guilds(ctx.guild)

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="rolebind")
    async def bind_role_to_reactions(
        self,
        ctx: commands.Context,
        role: discord.Role,
        channel: discord.TextChannel,
        msgid: int,
        emoji: str,
    ):
        """
        Binds a role to a reaction on a message...

        The role is only given if the criteria for it are met. 
        Make sure you configure the other settings for a role in [p]roleset
        """

        if not await self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        try:
            message = await channel.fetch_message(msgid)
        except discord.DiscordException:
            return await ctx.maybe_send_embed("No such message")

        _emoji = discord.utils.find(lambda e: str(e) == emoji, self.bot.emojis)
        if _emoji is None:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.DiscordException:
                return await ctx.maybe_send_embed("No such emoji")
            else:
                _emoji = emoji
                eid = emoji
        else:
            eid = _emoji.id

        if not any(str(r) == emoji for r in message.reactions):
            try:
                await message.add_reaction(_emoji)
            except discord.DiscordException:
                return await ctx.maybe_send_embed(
                    "Hmm, that message couldn't be reacted to"
                )

        cfg = self.config.custom("REACTROLE", message.id, eid)
        await cfg.set(
            {
                "roleid": role.id,
                "channelid": message.channel.id,
                "guildid": role.guild.id,
            }
        )
        await ctx.send(
            f"Remember, the reactions only function according to "
            f"the rules set for the roles using `{ctx.prefix}roleset`",
            delete_after=30,
        )

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="roleunbind")
    async def unbind_role_from_reactions(
        self, ctx: commands.Context, role: discord.Role, msgid: int, emoji: str
    ):
        """
        unbinds a role from a reaction on a message
        """

        if not await self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        await self.config.custom("REACTROLE", msgid, emoji).clear()
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="roleset", autohelp=True)
    async def rgroup(self, ctx: commands.Context):
        """
        Settings for role requirements
        """
        pass

    @rgroup.command(name="viewrole")
    async def rg_view_role(self, ctx: commands.Context, *, role: discord.Role):
        """
        Views the current settings for a role
        """

        rsets = await self.config.role(role).all()

        output = (
            f"This role:\n{'is' if rsets['self_role'] else 'is not'} self assignable"
            f"\n{'is' if rsets['self_removable'] else 'is not'} self removable"
        )
        if rsets["requires_any"]:
            rstring = ", ".join(
                r.name for r in ctx.guild.roles if r.id in rsets["requires_any"]
            )
            output += f"\nThis role requires any of the following roles: {rstring}"
        if rsets["requires_all"]:
            rstring = ", ".join(
                r.name for r in ctx.guild.roles if r.id in rsets["requires_all"]
            )
            output += f"\nThis role requires all of the following roles: {rstring}"
        if rsets["exclusive_to"]:
            rstring = ", ".join(
                r.name for r in ctx.guild.roles if r.id in rsets["exclusive_to"]
            )
            output += (
                f"\nThis role is mutually exclusive to the following roles: {rstring}"
            )

        for page in pagify(output):
            await ctx.send(page)

    @rgroup.command(name="cost")
    async def make_purchasable(self, ctx, cost: int, *, role: discord.Role):
        """
        Makes a role purchasable for a specified cost. 
        Cost must be a number greater than 0.
        A cost of exactly 0 can be used to remove purchasability.
        
        Purchase eligibility still follows other rules including self assignable.
        
        Warning: If these roles are bound to a reaction, 
        it will be possible to gain these without paying. 
        """

        if not await self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        if cost < 0:
            return await ctx.send_help()

        await self.config.role(role).cost.set(cost)
        if cost == 0:
            await ctx.send(f"{role.name} is no longer purchasable.")
        else:
            await ctx.send(f"{role.name} is purchasable for {cost}")

    @rgroup.command(name="forbid")
    async def forbid_role(
        self, ctx: commands.Context, role: discord.Role, *, user: discord.Member
    ):
        """
        Forbids a user from gaining a specific role.
        """
        async with self.config.member(user).forbidden() as fb:
            if role.id not in fb:
                fb.append(role.id)
            else:
                await ctx.send("Role was already forbidden")
        await ctx.tick()

    @rgroup.command(name="unforbid")
    async def unforbid_role(
        self, ctx: commands.Context, role: discord.Role, *, user: discord.Member
    ):
        """
        Unforbids a user from gaining a specific role.
        """
        async with self.config.member(user).forbidden() as fb:
            if role.id in fb:
                fb.remove(role.id)
            else:
                await ctx.send("Role was not forbidden")
        await ctx.tick()

    @rgroup.command(name="exclusive")
    async def set_exclusivity(self, ctx: commands.Context, *roles: discord.Role):
        """
        Takes 2 or more roles and sets them as exclusive to eachother
        """

        _roles = set(roles)

        if len(_roles) < 2:
            return await ctx.send("You need to provide at least 2 roles")

        for role in _roles:
            async with self.config.role(role).exclusive_to() as ex_list:
                ex_list.extend(
                    [r.id for r in _roles if r != role and r.id not in ex_list]
                )
        await ctx.tick()

    @rgroup.command(name="unexclusive")
    async def unset_exclusivity(self, ctx: commands.Context, *roles: discord.Role):
        """
        Takes any number of roles, and removes their exclusivity settings
        """

        _roles = set(roles)

        if not _roles:
            return await ctx.send("You need to provide at least a role to do this to")

        for role in _roles:
            ex_list = await self.config.role(role).exclusive_to()
            ex_list = [idx for idx in ex_list if idx not in [r.id for r in _roles]]
            await self.config.role(role).exclusive_to.set(ex_list)
        await ctx.tick()

    @rgroup.command(name="sticky")
    async def setsticky(self, ctx, role: discord.Role, sticky: bool = None):
        """
        sets a role as sticky if used without a settings, gets the current ones
        """

        if sticky is None:
            is_sticky = await self.config.role(role).sticky()
            return await ctx.send(
                "{role} {verb} sticky".format(
                    role=role.name, verb=("is" if is_sticky else "is not")
                )
            )

        await self.config.role(role).sticky.set(sticky)
        if sticky:
            for m in role.members:
                async with self.config.member(m).roles() as rids:
                    if role.id not in rids:
                        rids.append(role.id)

        await ctx.tick()

    @rgroup.command(name="requireall")
    async def reqall(
        self, ctx: commands.Context, role: discord.Role, *roles: discord.Role
    ):
        """
        Sets the required roles to gain a role

        Takes a role plus zero or more other roles (as requirements for the first)
        """

        rids = [r.id for r in roles]
        await self.config.role(role).requires_all.set(rids)
        await ctx.tick()

    @rgroup.command(name="requireany")
    async def reqany(
        self, ctx: commands.Context, role: discord.Role, *roles: discord.Role
    ):
        """
        Sets a role to require already having one of another

        Takes a role plus zero or more other roles (as requirements for the first)
        """

        rids = [r.id for r in (roles or [])]
        await self.config.role(role).requires_any.set(rids)
        await ctx.tick()

    @rgroup.command(name="selfrem")
    async def selfrem(self, ctx, role: discord.Role, removable: bool = None):
        """
        Sets if a role is self-removable (default False)

        use without a setting to view current
        """

        if removable is None:
            is_removable = await self.config.role(role).self_removable()
            return await ctx.send(
                "{role} {verb} self-removable".format(
                    role=role.name, verb=("is" if is_removable else "is not")
                )
            )

        await self.config.role(role).self_removable.set(removable)
        await ctx.tick()

    @rgroup.command(name="selfadd")
    async def selfadd(self, ctx, role: discord.Role, assignable: bool = None):
        """
        Sets if a role is self-assignable via command
        
        (default False)

        use without a setting to view current
        """

        if assignable is None:
            is_assignable = await self.config.role(role).self_role()
            return await ctx.send(
                "{role} {verb} self-assignable".format(
                    role=role.name, verb=("is" if is_assignable else "is not")
                )
            )

        await self.config.role(role).self_role.set(assignable)
        await ctx.tick()

    @checks.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    @commands.group(name="srole", autohelp=True)
    async def srole(self, ctx: commands.Context):
        """
        Self assignable role commands
        """
        pass

    @srole.command(name="buy")
    async def srole_buy(self, ctx: commands.Context, *, role: discord.Role):
        """
        Purchase a role
        """
        try:
            remove = await self.is_self_assign_eligible(ctx.author, role)
            eligible = await self.config.role(role).self_role()
            cost = await self.config.role(role).cost()
        except RoleManagementException:
            eligible = False
        except PermissionOrHierarchyException:
            await ctx.send(
                "I cannot assign roles which I can not manage. (Discord Hierarchy)"
            )
        else:
            if not eligible:
                return await ctx.send(
                    f"You aren't allowed to add `{role}` to yourself {ctx.author.mention}!"
                )

            if not cost:
                return await ctx.send(
                    "This role doesn't have a cost. Please try again using `[p]srole add`."
                )

            currency_name = await bank.get_currency_name(ctx.guild)

            try:
                await bank.withdraw_credits(ctx.author, cost)
            except ValueError:
                return await ctx.send(
                    f"You don't have enough {currency_name} (Cost: {cost})"
                )
            else:
                await self.update_roles_atomically(
                    who=ctx.author, give=[role], remove=remove
                )
                await ctx.tick()

    @srole.command(name="add")
    async def sadd(self, ctx: commands.Context, *, role: discord.Role):
        """
        Join a role
        """
        try:
            remove = await self.is_self_assign_eligible(ctx.author, role)
            eligible = await self.config.role(role).self_role()
            cost = await self.config.role(role).cost()
        except RoleManagementException:
            eligible = False
        except PermissionOrHierarchyException:
            await ctx.send(
                "I cannot assign roles which I can not manage. (Discord Hierarchy)"
            )
        else:
            if not eligible:
                await ctx.send(
                    f"You aren't allowed to add `{role}` to yourself {ctx.author.mention}!"
                )

            elif cost:
                await ctx.send(
                    "This role is not free. "
                    "Please use `[p]srole buy` if you would like to purchase it."
                )
            else:
                await self.update_roles_atomically(
                    who=ctx.author, give=[role], remove=remove
                )
                await ctx.tick()

    @srole.command(name="remove")
    async def srem(self, ctx: commands.Context, *, role: discord.Role):
        """
        leave a role
        """
        if await self.config.role(role).self_removable():
            await self.update_roles_atomically(who=ctx.author, remove=[role])
            await ctx.tick()
        else:
            await ctx.send(
                f"You aren't allowed to remove `{role}` from yourself {ctx.author.mention}!`"
            )
