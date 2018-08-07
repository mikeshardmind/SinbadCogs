import discord
from redbot.core import commands
from typing import List, Tuple, Optional

from .abc import MixinMeta
from .exceptions import (
    ConflictingRoleException,
    MissingRequirementsException,
    PermissionOrHierarchyException,
)


class UtilMixin(MixinMeta):
    """
    Mixin for utils, some of which need things stored in the class
    """

    async def update_roles_atomically(
        self,
        who: discord.Member,
        give: List[discord.Role] = None,
        remove: List[discord.Role] = None,
    ):
        """
        Give and remove roles as a single op with some slight sanity
        wrapping
        """
        me = who.guild.me
        give = give or []
        remove = remove or []
        roles = [r for r in who.roles if r not in remove]
        roles.extend([r for r in give if r not in roles])
        if sorted(roles) == sorted(who.roles):
            return
        if (
            any(r >= me.top_role for r in roles)
            or not me.guild_permissions.manage_roles
        ):
            raise discord.Forbidden("Can't do that.")
        await who.edit(roles=roles)

    async def all_are_valid_roles(self, ctx, *roles: discord.Role) -> bool:
        """
        Quick heirarchy check on a role set in syntax returned
        """
        author = ctx.author
        author_allowed = (
            (ctx.guild.owner == author)
            or all(ctx.author.top_role > role for role in roles)
            or await ctx.bot.is_owner(ctx.author)
        )
        bot_allowed = ctx.guild.me.guild_permissions.manage_roles and all(
            ctx.guild.me.top_role > role for role in roles
        )
        return author_allowed and bot_allowed

    async def is_self_assign_eligible(
        self, who: discord.Member, role: discord.Role
    ) -> List[discord.Role]:
        """
        Returns a list of roles to be removed if this one is added, or raises an
        exception
        """
        ret: List[discord.Role] = []

        await self.check_required(who, role)

        ret = await self.check_exclusivity(who, role)

        guild = who.guild
        if not guild.me.guild_permissions.manage_roles or role > guild.me.top_role:
            raise PermissionOrHierarchyException()

        return ret

    async def check_required(self, who: discord.Member, role: discord.Role) -> None:
        """
        Raises an error on missing reqs
        """

        req_any_fail: list = []
        req_all_fail: list = []

        async with self.config.role(role).requires_any() as req_any:
            if req_any and not any(r.id in req_any for r in who.roles):
                req_any_fail = req_any

        async with self.config.role(role).requires_all() as req_all:
            req_all_fail = list(set(req_all) - set(who.roles))

        if req_any_fail or req_all_fail:
            raise MissingRequirementsException(
                miss_all=req_all_fail, miss_any=req_any_fail
            )

        return None

    async def check_exclusivity(
        self, who: discord.Member, role: discord.Role
    ) -> List[discord.Role]:
        """
        Returns a list of roles to remove, or raises an error
        """
        ret: List[discord.Role]

        async with self.config.role(role).exclusive_to() as ex:
            if any(r.id in ex for r in who.roles):
                conflicts = [r for r in who.roles if r.id in ex]
                if await self.config.role(role).toggle_on_exclusive():
                    ret = conflicts
                else:
                    raise ConflictingRoleException(conflicts=conflicts)

        return ret
