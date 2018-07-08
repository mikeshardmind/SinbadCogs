import discord
from redbot.core import commands


class UtilMixin:
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

    def all_are_valid_roles(self, ctx, *roles: discord.Role) -> bool:
        """
        Quick heirarchy check on a role set in syntax returned
        """
        author = ctx.author
        author_allowed = ctx.guild.owner == author or all(
            ctx.author.top_role > role for role in roles
        )
        bot_allowed = ctx.guild.me.guild_permissions.manage_roles and all(
            ctx.guild.me.top_role > role for role in roles
        )
        return author_allowed and bot_allowed

    async def is_self_assign_eligible(
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
