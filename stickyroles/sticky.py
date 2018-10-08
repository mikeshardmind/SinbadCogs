from typing import Any
import discord
from redbot.core.config import Config
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import pagify, humanize_list


class StickyRoles(commands.Cog):

    __author__ = "mikeshardmind"
    __version__ = "1.1.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_member(roles=[])
        self.config.register_role(sticky=False)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command()
    async def liststicky(self, ctx):
        """
        Shows the roles which are sticky.
        """
        data = await self.config.all_roles()
        rids = {k for k, v in data.items() if v['sticky']}
        role_names = {r.name for r in ctx.guild.roles if r.id in rids}
        if not role_names:
            return await ctx.send("No sticky roles")
        
        output = "Sticky roles:\n" + humanize_list(role_names)
        for page in pagify(output):
            await ctx.send(page)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command()
    async def setsticky(self, ctx, role: discord.Role):
        """
        Sets a role as sticky
        """

        await self.config.role(role).sticky.set(True)
        for m in role.members:
            async with self.config.member(m).roles() as rids:
                if role.id not in rids:
                    rids.append(role.id)
        await ctx.tick()

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command()
    async def remsticky(self, ctx, role: discord.Role):
        """
        Removes the stickyness of a role
        """
        await self.config.role(role).sticky.set(False)
        async with self.config._get_base_group("MEMBER", ctx.guild.id)() as gdata:
            for _k, rids in gdata.items():
                if role.id in rids:
                    rids.remove(role.id)
        await ctx.tick()

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
