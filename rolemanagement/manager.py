import discord
from typing import Tuple, List
from redbot.core import checks, commands
from redbot.core.config import Config


class RoleManagement:
    """
    Cog for role management
    """

    __author__ = "mikeshardmind"
    __version__ = "0.0.1a"

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
        )  # ID : Message.id, str(React)

    async def is_eligible(
        self, who: discord.Member, role: discord.Role
    ) -> Tuple[bool, list]:

        guild = who.guild
        if not guild.me.guild_permissions.manage_roles or role > guild.me.top_role:
            return False, None

#
#        if await self.config.role(role).protected():
#            return False, None
#
#        async with self.config.role(role).requires_any() as req_any:
#            if req_any and not any(r.id in req_any for r in who.roles):
#                return False, None
#
#        async with self.config.role(role).requires_all() as req_all:
#            if not all(r.id in req_all for r in who.roles):
#                return False, None
#
#        async with self.config.role(role).exclusive_to() as ex:
#            if any(r.id in ex for r in who.roles):
#                if await self.config.role(role).toggle_on_exclusive():
#                    return True, [r for r in who.roles if r.id in ex]
#                else:
#                    return False, None
#
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

        cfg = self.config.custom("REACTROLE", payload.message_id, str(payload.emoji))
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
        self, who: discord.Member, give: List[discord.Role], remove: List[discord.Role]
    ):
        """
        Give and remove roles as a single op

        This can fail silently, and I don't really care.
        This should only be used after already verifying the
        operation is valid based on permissions and heirarchy
        """

        print("K")
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

        if not any(str(r) == emoji for r in message.reactions):
            try:
                await message.add_reaction(_emoji)
            except Exception:
                return await ctx.maybe_send_embed(
                    "Hmm, that message couldn't be reacted to"
                )

        cfg = self.config.custom("REACTROLE", message.id, str(_emoji))
        await cfg.roleid.set(role.id)
        await ctx.tick()

    # End commands
