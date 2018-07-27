import discord
from redbot.core import checks, commands
from redbot.core.config import Config
from .utils import UtilMixin
from .massmanager import MassManagementMixin
from .events import EventMixin
from .notifications import NotificationMixin


class RoleManagement(UtilMixin, MassManagementMixin, EventMixin, NotificationMixin):
    """
    Cog for role management
    """

    __author__ = "mikeshardmind"
    __version__ = "2.0.0a"

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
            toggle_on_exclusive=False,
            self_removable=False,
            self_role=False,
            protected=False,
        )
        self.config.register_member(roles=[])
        self.config.register_custom(
            "REACTROLE", roleid=None
        )  # ID : Message.id, str(React)
        self.config.register_guild(notify_channel=None)
        super().__init__()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_server=True)
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
        binds a role to a reaction on a message
        """

        if not self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        message = await channel.get_message(msgid)
        if not message:
            return await ctx.maybe_send_embed("No such message")

        _emoji = discord.utils.find(lambda e: str(e) == emoji, self.bot.emojis)
        if _emoji is None:
            try:
                ctx.message.add_reaction(emoji)
            except:
                return await ctx.maybe_send_embed("No such emoji")
            else:
                _emoji = emoji
                eid = emoji
        else:
            eid = _emoji.id

        if not any(str(r) == emoji for r in message.reactions):
            try:
                await message.add_reaction(_emoji)
            except Exception:
                return await ctx.maybe_send_embed(
                    "Hmm, that message couldn't be reacted to"
                )

        cfg = self.config.custom("REACTROLE", message.id, eid)
        await cfg.roleid.set(role.id)
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_server=True)
    @commands.command(name="roleunbind")
    async def unbind_role_from_reactions(
        self,
        ctx: commands.Context,
        role: discord.Role,
        channel: discord.TextChannel,
        msgid: int,
        emoji: str,
    ):
        """
        unbinds a role from a reaction on a message
        """

        if not self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        cfg = self.config.custom("REACTROLE", msgid, str(emoji))
        await cfg.roleid.clear()
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

    @rgroup.command(name="unexclusive")
    async def unset_exclusivity(self, ctx: commands.Context, *roles: discord.Role):
        """
        Takes any number of roles, and removes their exclusivity settings
        """

        _roles = set(roles)

        if len(roles) < 1:
            return await ctx.send("You need to provide at least a role to do this to")

        for role in _roles:
            ex_list = await self.config.role(role).exclusive_to()
            ex_list = [idx for idx in ex_list if idx not in [r.id for r in _roles]]
            await self.config.role(role).exclusive_to.set(ex_list)

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
                "{role} {verb} sticky".format(
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
                "{role} {verb} sticky".format(
                    role=role.name, verb=("is" if is_assignable else "is not")
                )
            )

        await self.config.role(role).self_role.set(assignable)
        await ctx.tick()

    @commands.guild_only()
    @commands.group(name="srole", autohelp=True)
    async def srole(self, ctx: commands.Context):
        """
        Self assignable role commands
        """
        pass

    @srole.command(name="add")
    async def sadd(self, ctx: commands.Context, *, role: discord.Role):
        """
        Join a role
        """
        try:
            remove = await self.is_self_assign_eligible(ctx.author, role)
            eligible = await self.config.role(role).self_role()
        except Exception:
            eligible = False

        if not eligible:
            await ctx.send(
                f"You aren't allowed to add `{role}` to yourself {ctx.author.mention}!"
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
            await self.update_roles_atomically(who=ctx.author, give=None, remove=[role])
            await ctx.tick()
        else:
            await ctx.send(
                f"You aren't allowed to remove `{role}` from yourself {ctx.author.mention}!`"
            )
