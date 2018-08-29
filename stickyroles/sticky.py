import discord
from redbot.core.config import Config
from redbot.core import commands, checks


class StickyRoles:

    __author__ = "mikeshardmind"
    __version__ = "1.0.0b"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_member(roles=[])
        self.config.register_role(sticky=False)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.command()
    async def setsticky(self, ctx, role: discord.Role, sticky: bool = None):
        """
        sets a role as sticky
        """

        if sticky is None:
            is_sticky = await self.config.role(role).sticky()
            return await ctx.send(
                "{role} {verb} sticky".format(
                    role=role.name, verb=("is" if is_sticky else "is not")
                )
            )

        await self.config.role(role).sticky.set(sticky)
        if sticky:
            for m in role.members:
                async with self.config.member(m).roles() as rids:
                    if role.id not in rids:
                        rids.append(role.id)

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
