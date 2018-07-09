import discord


class EventMixin:
    def __init__(self, *args, **kwargs):
        pass

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

        can, remove = await self.is_self_assign_eligible(member, role)
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
