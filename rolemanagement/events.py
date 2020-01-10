from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, cast

import discord
from redbot.core import commands

from .abc import MixinMeta
from .exceptions import RoleManagementException, PermissionOrHierarchyException


class EventMixin(MixinMeta):
    def verification_level_issue(self, member: discord.Member) -> bool:
        """
        Returns True if this would bypass verification level settings

        prevent react roles from bypassing time limits.
        It's exceptionally dumb that users can react while
        restricted by verification level, but that's Discord.
        They block reacting to blocked users, but interacting
        with entire guilds by reaction before hand? A-OK. *eyerolls*

        Can't check the email/2FA, blame discord for allowing people to react with above.
        """
        guild: discord.Guild = member.guild
        now = datetime.utcnow()
        level: int = guild.verification_level.value

        if level >= 3 and member.created_at + timedelta(minutes=5) > now:  # medium
            return True

        if level >= 4:  # high
            assert member.joined_at is not None, "mypy"  # nosec
            if member.joined_at + timedelta(minutes=10) > now:
                return True

        return False

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        DEP-WARN
        Section has been optimized assuming member._roles
        remains an iterable containing snowflakes
        """
        if before._roles == after._roles:
            return

        sym_diff = set(before._roles).symmetric_difference(set(after._roles))

        gained, lost = [], []
        for r in sym_diff:
            if await self.config.role_from_id(r).sticky():
                if r in before.roles:
                    lost.append(r)
                else:
                    gained.append(r)

        async with self.config.member(after).roles() as rids:
            for r in lost:
                while r in rids:
                    rids.remove(r)
            for r in gained:
                if r not in rids:
                    rids.append(r)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if not guild.me.guild_permissions.manage_roles:
            return

        async with self.config.member(member).roles() as rids:
            to_add: List[discord.Role] = []
            for _id in rids:
                role = discord.utils.get(guild.roles, id=_id)
                if not role:
                    continue
                if await self.config.role(role).sticky():
                    to_add.append(role)
            if to_add:
                to_add = [r for r in to_add if r < guild.me.top_role]
                await member.add_roles(*to_add)

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.raw_models.RawReactionActionEvent
    ):
        if not payload.guild_id:
            return

        emoji = payload.emoji
        eid = emoji.id if emoji.is_custom_emoji() else str(emoji)
        cfg = self.config.custom("REACTROLE", payload.message_id, eid)
        rid = await cfg.roleid()
        if rid is None or not await self.config.role_from_id(rid).self_role():
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild:
            await self.maybe_update_guilds(guild)
        else:
            return
        member = guild.get_member(payload.user_id)

        if self.verification_level_issue(member):
            return

        if member.bot:
            return
        role = guild.get_role(rid)
        if role in member.roles:
            return

        try:
            remove = await self.is_self_assign_eligible(member, role)
        except (RoleManagementException, PermissionOrHierarchyException):
            pass
        else:
            await self.update_roles_atomically(who=member, give=[role], remove=remove)

    @commands.Cog.listener()
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

        if await self.config.role_from_id(rid).self_removable():
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            if member.bot:
                return
            role = cast(discord.Role, discord.utils.get(guild.roles, id=rid))
            if role not in member.roles:
                return
            if guild.me.guild_permissions.manage_roles and guild.me.top_role > role:
                await self.update_roles_atomically(who=member, give=None, remove=[role])
