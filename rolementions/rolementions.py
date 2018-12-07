import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from typing import Union

MemberOrRole = Union[discord.Role, discord.Member]


class RoleMentions(commands.Cog):
    """
    Stuff for mentioning roles.

    You can utilize the permissions cog to restrict usage by channel if needed.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631113035100160)
        self.config.register_role(mentionable_by=[], needs_fix=False)
        self.config.register_custom(
            "CMENTION", usable_by=[], to_mention=[], template=None
        )  # (guild.id, name) -> data

    @commands.guild_only()
    @commands.group()
    async def rmentionset(self, ctx):
        """
        Configuration settings for RoleMentions
        """
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @rmentionset.command()
    async def mentionableby(
        self,
        ctx: commands.Context,
        role: discord.Role,
        who: commands.Greedy[MemberOrRole] = None,
    ):
        """
        Adds one or more users or roles to the people who can mention a role.
        
        I suggest using an ID or mention of the roles or members for safety,
        but I'm not stopping you from using this unsafely.
        """

        if not who:
            return await ctx.send_help()

        added, not_added = set(), set()
        async with self.config.role(role).mentionable_by() as ids:
            for item in who:
                if item.id in ids:
                    not_added.add(item)
                else:
                    ids.append(item.id)
                    added.add(item)

        if not added:
            await ctx.send("Those were all already allowed to mention that role.")
        else:
            if not_added:
                message = (
                    f"Added to the list of people able to mention: {', '.join(map(str, added))}"
                    f"\nAlready allowed to mention: {', '.join(map(str, not_added))}"
                )
            else:
                message = f"Added to the list of people able to mention: {', '.join(map(str, added))}"
            await ctx.send(message)

    @rmentionset.command()
    async def removementionableby(
        self,
        ctx: commands.Context,
        role: discord.Role,
        who: commands.Greedy[MemberOrRole] = None,
    ):
        """
        Adds one or more users or roles to the people who can mention a role.
        
        I suggest using an ID or mention of the roles or members for safety,
        but I'm not stopping you from using this unsafely.
        """

        if not who:
            return await ctx.send_help()

        removed, not_removed = set(), set()
        async with self.config.role(role).mentionable_by() as ids:
            for item in who:
                if item.id in ids:
                    ids.remove(item.id)
                    removed.add(item)
                else:
                    not_removed.add(item)

        if not removed:
            await ctx.send("None of those were allowed to mention that role.")
        else:
            if not_removed:
                message = (
                    f"Removed from the list of people able to mention: "
                    f"{', '.join(map(str, removed))}"
                    f"\nNot already allowed to mention: "
                    f"{', '.join(map(str, not_removed))}"
                )
            else:
                message = (
                    f"Removed from the list of people able to mention: "
                    f"{', '.join(map(str, removed))}"
                )
            await ctx.send(message)

    @rmentionset.command()
    async def clearallowed(self, ctx, role: discord.Role):
        """
        Clears all allowed users of the role mention for a role.
        """
        await self.config.role(role).mentionable_by.clear()
        await ctx.tick()

    @commands.command()
    async def rmention(self, ctx, *, roles: discord.Role = None):
        """
        Attempt to mention one or more roles
        """
        if not roles:
            return await ctx.send_help()

        role_data = await self.config.all_roles()
        author_ids = set([r.id for r in ctx.author.roles])
        author_ids.add(ctx.author.id)

        def grabber(role_obj):
            try:
                if set(role_data[role_obj.id]["mentionable_by"]) & author_ids:
                    return True
            except KeyError:
                pass
            return False

        if not all(grabber(r) for r in roles):
            return await ctx.send(
                "One or more of those roles is not mentionable by this command"
            )
