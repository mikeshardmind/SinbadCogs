from __future__ import annotations

import re
from typing import List

import discord

from .abc import MixinMeta
from .exceptions import (
    ConflictingRoleException,
    MissingRequirementsException,
    PermissionOrHierarchyException,
)

variation_stripper_re = re.compile(r"[\ufe00-\ufe0f]")


class UtilMixin(MixinMeta):
    """
    Mixin for utils, some of which need things stored in the class
    """

    def strip_variations(self, s: str) -> str:
        """
        Normalizes emoji, removing variation selectors
        """
        return variation_stripper_re.sub("", s)

    async def update_roles_atomically(
        self,
        *,
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
        heirarchy_testing = give + remove
        roles = [r for r in who.roles if r not in remove]
        roles.extend([r for r in give if r not in roles])
        if sorted(roles) == sorted(who.roles):
            return
        if (
            any(r >= me.top_role for r in heirarchy_testing)
            or not me.guild_permissions.manage_roles
        ):
            raise PermissionOrHierarchyException("Can't do that.")
        await who.edit(roles=roles)

    async def all_are_valid_roles(self, ctx, *roles: discord.Role) -> bool:
        """
        Quick heirarchy check on a role set in syntax returned
        """
        author = ctx.author
        guild = ctx.guild

        # Author allowed
        if not (
            (guild.owner == author)
            or all(author.top_role > role for role in roles)
            or await ctx.bot.is_owner(ctx.author)
        ):
            return False

        # Bot allowed
        if not (
            guild.me.guild_permissions.manage_roles
            and (
                guild.me == guild.owner
                or all(guild.me.top_role > role for role in roles)
            )
        ):
            return False

        # Sanity check on managed roles
        if any(role.managed for role in roles):
            return False

        return True

    async def is_self_assign_eligible(
        self, who: discord.Member, role: discord.Role
    ) -> List[discord.Role]:
        """
        Returns a list of roles to be removed if this one is added, or raises an
        exception
        """

        await self.check_required(who, role)

        ret: List[discord.Role] = await self.check_exclusivity(who, role)

        forbidden = await self.config.member(who).forbidden()
        if role.id in forbidden:
            raise PermissionOrHierarchyException()

        guild = who.guild
        if not guild.me.guild_permissions.manage_roles or role > guild.me.top_role:
            raise PermissionOrHierarchyException()

        return ret

    async def check_required(self, who: discord.Member, role: discord.Role) -> None:
        """
        Raises an error on missing reqs
        """

        req_any = await self.config.role(role).requires_any()
        req_any_fail = req_any[:]
        if req_any:
            for idx in req_any:
                if who._roles.has(idx):
                    req_any_fail = []
                    break

        req_all_fail = [
            idx
            for idx in await self.config.role(role).requires_all()
            if not who._roles.has(idx)
        ]

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

        data = await self.config.all_roles()
        ex = data.get(role.id, {}).get("exclusive_to", [])
        conflicts: List[discord.Role] = [r for r in who.roles if r.id in ex]

        for r in conflicts:
            if not data.get(r.id, {}).get("self_removable", False):
                raise ConflictingRoleException(conflicts=conflicts)
        return conflicts

    async def maybe_update_guilds(self, *guilds: discord.Guild):
        _guilds = [g for g in guilds if not g.unavailable and g.large and not g.chunked]
        if _guilds:
            await self.bot.request_offline_members(*_guilds)
