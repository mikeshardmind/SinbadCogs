import discord
from typing import Tuple, List
from redbot.core import checks, commands
from redbot.core.config import Config


class RoleManagement:
    """
    Cog for role management
    """

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
            protected=False,
        )
        self.config.register_custom(
            "REACTROLE", roleid=None
        )  # IDs : Message.id, str(React)
        self.config.register_guild(respect_heirarchy=True)  # TODO: configurable

    async def is_eligible(
        self, who: discord.Member, role: discord.Role
    ) -> Tuple[bool, list]:

        if not guild.me.guild_permissions.manage_roles or role > guild.me.top_role:
            return False, None

        if await self.config.role(role).protected():
            return False, None

        async with self.config.role(role).requires_any as req_any:
            if req_any and not any(r.id in req_any for r in who.roles):
                return False, None

        async with self.config.role(role).requires_all as req_all:
            if not all(r.id in req_all for r in who.roles):
                return False, None

        async with self.config.role(role).exclusive_to as ex:
            if any(r.id in ex for r in who.roles):
                if await self.config.role(role).toggle_on_exclusive():
                    return True, [r for r in who.roles if r.id in ex]
                else:
                    return False, None

        return True, None

    # Start Events
    async def on_raw_reaction_add(
        self, payload: discord.raw_models.RawReactionActionEvent
    ):
        if not payload.guild_id:
            return

        cfg = self.config.custom("REACTROLE", payload.message_id, str(payload.emoji))
        rid = await cfg.roleid()

        if rid is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
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

        cfg = self.config.custom("REACTROLE", payload.message_id, str(payload.emoji))
        rid = await cfg.roleid()

        if rid is None:
            return

        if await self.config.custom("ROLE", discord.Object(rid)).self_removable():
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = discord.utils.get(guild.roles, id=rid)
            if role not in member.roles:
                return
            if guild.me.guild_permissions.manage_roles and guild.me.top_role > role:
                await self.update_roles_atomically(member, give=None, remove=[role])

    # end events

    async def update_roles_atomically(
        self, who: discord.Member, give: List[discord.Role], remove: List[discord.Role]
    ):
        """
        Give and remove roles as a single op
        """

        rids = [r.id for r in who.roles if r not in remove]
        rids.extend([r.id for r in give])
        payload = {"roles": rids}

        await self.bot.http.request(
            discord.http.Route(
                "PATCH",
                "/guilds/{guild_id}/members/{user_id}",
                guild_id=who.guild.id,
                user_id=who.id,
            ),
            reason="redbot.sinbadcogs.rolemanagement update",
            json=payload,
        )

    # Start commands
    # TODO: Commands
    # End commands
