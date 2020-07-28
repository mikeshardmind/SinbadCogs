from __future__ import annotations

import re
from typing import Dict, List, TypedDict

import discord

from .abc import MixinMeta
from .exceptions import (
    ConflictingRoleException,
    MissingRequirementsException,
    PermissionOrHierarchyException,
    RoleManagementException,
)

variation_stripper_re = re.compile(r"[\ufe00-\ufe0f]")


class RoleSettings(TypedDict):
    requires_all: List[int]
    requires_any: List[int]
    self_removable: bool


class UtilMixin(MixinMeta):
    """
    Mixin for utils, some of which need things stored in the class
    """

    def get_top_role(self, member: discord.Member) -> discord.Role:
        """
        Workaround for behavior in GH-discord.py#4087
        """
        # DEP-WARN

        guild: discord.Guild = member.guild

        if len(member._roles) == 0:
            return guild.default_role

        return max(guild.get_role(rid) or guild.default_role for rid in member._roles)

    def strip_variations(self, s: str) -> str:
        """
        Normalizes emoji, removing variation selectors
        """
        return variation_stripper_re.sub("", s)

    def _can_remove(
        self,
        data: Dict[int, RoleSettings],
        role_to_remove: discord.Role,
        remaining_roles: List[discord.Role],
    ) -> List[discord.Role]:
        """
        Need to test this later,
        might be simpler to just block on any req and force the user to
        remove themselves.

        Technically speaking, this can also hit a recursion limit
        """

        to_drop: List[discord.Role] = []

        for role_id, role_data in data.items():

            others = [r for r in remaining_roles if r.id != role_id]
            role = next(filter(lambda r: r.id == role_id, remaining_roles))

            if role_to_remove.id in role_data.get("requires_all", []):
                if not role_data.get("self_removable", False):
                    raise RoleManagementException()
                else:
                    to_drop.extend(self._can_remove(data, role, others))
                    to_drop.append(role)

            if role_to_remove.id in (r_any := role_data.get("requires_any", [])):
                if {r.id for r in remaining_roles}.isdisjoint(r_any):
                    if not role_data.get("self_removable", False):
                        raise RoleManagementException()
                    else:
                        to_drop.extend(self._can_remove(data, role, others))
                        to_drop.append(role)

        return list(dict.fromkeys(to_drop))

    async def safe_remove_role(
        self, *, who: discord.Member, role: discord.Role,
    ):
        """
        Ensures that removing this role doesn't violate other conditions
        """

        role_info = {
            rid: rdata
            for rid, rdata in (await self.config.all_roles()).items()
            if who._roles.has(rid)
        }

        to_drop = self._can_remove(role_info, role, [r for r in who.roles if r != role])

        await self.update_roles_atomically(who=who, remove=to_drop)

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
        hierarchy_testing = give + remove
        user_roles = sorted(who.roles)  # resort needed, see GH-discord.py#4087
        roles = [r for r in user_roles if r not in remove]
        roles.extend([r for r in give if r not in roles])
        if sorted(roles) == user_roles:
            return
        if (
            any(r >= self.get_top_role(me) for r in hierarchy_testing)
            or not me.guild_permissions.manage_roles
        ):
            raise PermissionOrHierarchyException("Can't do that.")
        await who.edit(roles=roles)

    async def all_are_valid_roles(
        self, ctx, *roles: discord.Role, detailed: bool = False
    ) -> bool:
        """
        Quick hierarchy check on a role set in syntax returned
        """
        author = ctx.author
        guild = ctx.guild

        # Author allowed

        if not guild.owner == author:
            auth_top = self.get_top_role(author)
            if not (
                all(auth_top > role for role in roles)
                or await ctx.bot.is_owner(ctx.author)
            ):
                if detailed:
                    raise RoleManagementException(
                        "You can't give away roles which are not below your top role."
                    )
                return False

        # Bot allowed

        if not guild.me.guild_permissions.manage_roles:
            if detailed:
                raise RoleManagementException("I can't manage roles.")
            return False

        if not guild.me == guild.owner:
            bot_top = self.get_top_role(guild.me)
            if not all(bot_top > role for role in roles):
                if detailed:
                    raise RoleManagementException(
                        "I can't give away roles which are not below my top role."
                    )
                return False

        # Sanity check on managed roles
        if any(role.managed for role in roles):
            if detailed:
                raise RoleManagementException(
                    "Managed roles can't be assigned by this."
                )
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
        if not guild.me.guild_permissions.manage_roles:
            if role > self.get_top_role(guild.me):
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
