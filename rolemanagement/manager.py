import discord
from typing import Tuple, List
from redbot.core import checks, commands
from redbot.core.config import Config


class RoleManagement:
    """
    Cog for role management
    """

    __author__ = "mikeshardmind"
    __version__ = "0.0.5a"

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

    async def is_eligible(
        self, who: discord.Member, role: discord.Role
    ) -> Tuple[bool, list]:

        guild = who.guild
        if not guild.me.guild_permissions.manage_roles or role > guild.me.top_role:
            return False, None

        if await self.config.role(role).protected():
            return False, None

        async with self.config.role(role).requires_any() as req_any:
            if req_any and not any(r.id in req_any for r in who.roles):
                return False, None

        async with self.config.role(role).requires_all() as req_all:
            if not all(r.id in req_all for r in who.roles):
                return False, None

        async with self.config.role(role).exclusive_to() as ex:
            if any(r.id in ex for r in who.roles):
                if await self.config.role(role).toggle_on_exclusive():
                    return True, [r for r in who.roles if r.id in ex]
                else:
                    return False, None

        return True, None

    # Start Events

    async def on_member_update(self, before, after):

        if before.roles == after.roles:
            return

        sym_diff = set(before.roles).symmetric_difference(set(after.roles))

        gained, lost = [], []
        for r in sym_diff:
            if await self.config.role(r).sticky():
                if r in before.roles:
                    lost.append(r)
                else:
                    gained.append(r)

        async with self.config.member(after).roles() as rids:
            for r in lost:
                while r.id in rids:
                    rids.remove(r.id)
            for r in gained:
                if r.id not in rids:
                    rids.append(r.id)

    async def on_member_join(self, member):
        guild = member.guild
        if not guild.me.guild_permissions.manage_roles:
            return

        async with self.config.member(member).roles() as rids:
            to_add = []
            for _id in rids:
                role = discord.utils.get(guild.roles, id=_id)
                if await self.config.role(role).sticky():
                    to_add.append(role)
            if to_add:
                to_add = [r for r in to_add if r < guild.me.top_role]
                await member.add_roles(*to_add)

    async def on_raw_reaction_add(
        self, payload: discord.raw_models.RawReactionActionEvent
    ):
        if not payload.guild_id:
            return

        emoji = payload.emoji
        eid = emoji.id if emoji.is_custom_emoji() else str(emoji)
        cfg = self.config.custom("REACTROLE", payload.message_id, eid)
        rid = await cfg.roleid()

        if rid is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot:
            return
        role = discord.utils.get(guild.roles, id=rid)
        if role in member.roles:
            return

        can, remove = await self.is_eligible(member, role)
        if can:
            await self.update_roles_atomically(member, give=[role], remove=remove)

    async def on_raw_reaction_remove(
        self, payload: discord.raw_models.RawReactionActionEvent
    ):
        if not payload.guild_id:
            return

        emoji = payload.emoji
        eid = emoji.id if emoji.is_custom_emoji() else str(emoji)
        cfg = self.config.custom("REACTROLE", payload.message_id, eid)
        rid = await cfg.roleid()

        if rid is None:
            return

        if await self.config.role(discord.Object(rid)).self_removable():
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            if member.bot:
                return
            role = discord.utils.get(guild.roles, id=rid)
            if role not in member.roles:
                return
            if guild.me.guild_permissions.manage_roles and guild.me.top_role > role:
                await self.update_roles_atomically(member, give=None, remove=[role])

    # End events
    async def update_roles_atomically(
        self,
        who: discord.Member,
        give: List[discord.Role] = None,
        remove: List[discord.Role] = None,
    ):
        """
        Give and remove roles as a single op
        """
        give = give or []
        remove = remove or []
        roles = [r for r in who.roles if r not in remove]
        roles.extend([r for r in give if r not in roles])
        if sorted(roles) == sorted(who.roles):
            return
        payload = {"roles": [r.id for r in roles]}
        await self.bot.http.request(
            discord.http.Route(
                "PATCH",
                "/guilds/{guild_id}/members/{user_id}",
                guild_id=who.guild.id,
                user_id=who.id,
            ),
            json=payload,
        )

    # Start commands
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

        if role >= ctx.author.top_role or (
            role >= ctx.guild.me.top_role and ctx.author != ctx.guild.owner
        ):
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

        if role >= ctx.author.top_role or (
            role >= ctx.guild.me.top_role and ctx.author != ctx.guild.owner
        ):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        cfg = self.config.custom("REACTROLE", message.id, eid)
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

    @rgroup.command("exclusive")
    async def set_exclusivity(self, ctx: commands.Context, *roles: discord.Role):
        """
        Takes 2 or more roles and sets them as exclusive to eachother
        """

        roles = set(roles)

        if len(roles) < 2:
            return await ctx.send("You need to provide at least 2 roles")

        for role in roles:
            async with self.config.role(role).exclusive_to() as ex_list:
                ex_list.extend(
                    [r.id for r in roles if r != role and r.id not in ex_list]
                )

    @rgroup.command("unexclusive")
    async def unset_exclusivity(self, ctx: commands.Context, *roles: discord.Role):
        """
        Takes any number of roles, and removes their exclusivity settings
        """

        roles = set(roles)

        if len(roles) < 1:
            return await ctx.send("You need to provide at least a role to do this to")

        for role in roles:
            ex_list = await self.config.role(role).exclusive_to()
            ex_list = [idx for idx in ex_list if idx not in [r.id for r in roles]]
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

    @rgroup.command(name="selfremoveable")
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

    @rgroup.command(name="selfassignable")
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
        eligible, remove = await self.is_eligible(ctx.author, role)
        eligible &= await self.config.role(role).self_role()
        if not eligible:
            return await ctx.send(
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

    # End commands
