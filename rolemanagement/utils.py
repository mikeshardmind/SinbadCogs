#   Copyright 2017-present Michael Hall
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import annotations

import re
from typing import List

import discord

from .abc import MixinMeta
from .exceptions import (
    ConflictingRoleException,
    MissingRequirementsException,
    PermissionOrHierarchyException,
    RoleManagementException,
)

variation_stripper_re = re.compile(r"[\ufe00-\ufe0f]")


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

    async def update_roles_atomically(
        self,
        *,
        who: discord.Member,
        give: List[discord.Role] = None,
        remove: List[discord.Role] = None,
    ):
        """
        Give and remove roles as a single op with a soundness check.
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

        # Bots can't assign managed roles
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
