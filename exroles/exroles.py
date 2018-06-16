import discord
from redbot.core import commands, Config, checks


class ExRoles:
    """
    Role exclusivity
    """

    __version__ = "0.0.0"
    __author__ = "mikeshardmind (Sinbad#0001)"

    def __init__(self, bot):
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(groupings={})

    @checks.admin_or_permissions(admininstrator=True)
    @commands.guild_only()
    @commands.group(autohelp=True)
    async def exroleset(self, ctx):
        """
        Commands for ExRole's config
        """
        pass

    @exroleset.command()
    async def group(self, ctx, name: str, *roles: discord.Role):
        """
        Make a group
        """

        seen = []
        for r in roles:
            if r not in seen:
                seen.append(r)

        if len(seen) != len(roles):
            await ctx.send(
                "You are a dumbass for putting the same role in "
                "multiple times, I fixed it for you."
            )

        if any(r >= ctx.guild.me.top_role for r in seen):
            return await ctx.send("I'm unable to give away roles higher than mine.")

        if ctx.author != ctx.guild.owner and any(
            r >= ctx.author.top_role for r in seen
        ):
            return await ctx.send("You can't give away roles higher than your own")

        async with self.config.guild(ctx.guild).groupings() as rgs:
            rgs.update({name: [r.id for r in seen]})

        await ctx.tick()

    @commands.guild_only()
    @commands.command(name="rjoin")
    async def join(self, ctx, role: discord.Role):
        """
        join a role
        """

        author = ctx.message.author
        avail = await self.get_joinable(author)

        if role not in avail:
            return await self.bot.say(
                "Role: {0.name} is not available to you, {1.mention}".format(
                    role, author
                )
            )

        try:
            await self.bot.add_roles(author, role)
        except Exception as e:
            await self.bot.say("Something went wrong")
        else:
            await self.bot.say("Role assigned")

    async def get_joinable(self, member: discord.Member):
        guild = member.guild
        async with self.config.guild(guild).groupings() as rgs:
            available = []
            for name, rids in rgs.items():
                set_roles = [r for r in guild.roles if r.id in rids]
                if set(member.roles).isdisjoint(set_roles):
                    available.extend(set_roles)
                else:
                    for role in set_roles:
                        while role in available:
                            available.remove(role)
        return available
