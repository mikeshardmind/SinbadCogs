import discord
from typing import Tuple, List
from redbot.core import checks, commands
from .converters import RoleSyntaxConverter, ComplexActionConverter, ComplexSearchConverter
import csv
import io


class MassManager:
    """
    Mass role operations
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0.1a"

    def __init__(self, bot):
        self.bot = bot

    async def update_roles_atomically(
        self,
        who: discord.Member,
        give: List[discord.Role] = [],
        remove: List[discord.Role] = [],
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

    def all_are_valid_roles(self, ctx, role_dict: dict) -> bool:
        """
        Quick heirarchy check on a role set in syntax returned
        """
        roles = role_dict["+"] + role_dict["-"]
        author = ctx.author
        author_allowed = ctx.guild.owner == author or all(
            ctx.author.top_role > role for role in roles
        )
        bot_allowed = ctx.guild.me.guild_permissions.manage_roles and all(
            ctx.guild.me.top_role > role for role in roles
        )
        return author_allowed and bot_allowed

    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.group(name="massrole", autohelp=True, aliases=['mrole'])
    async def mrole(self, ctx: commands.Context):
        """
        Commands for mass role management
        """
        pass

    @mrole.group(name="dynomode", autohelp=True)
    async def drole(self, ctx: commands.Context):
        """
        Provides syntax similar to dyno bots for ease of transition
        """
        pass

    @drole.command(name="bots")
    async def mrole_bots(self, ctx: commands.Context, *, roles: RoleSyntaxConverter):
        """
        adds/removes roles to all bots.

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole bots +RoleToGive, -RoleToRemove

        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in ctx.guild.members:
            if member.bot:
                await self.update_roles_atomically(
                    member, give=roles["+"], remove=roles["-"]
                )

        await ctx.tick()

    @drole.command(name="all")
    async def mrole_all(self, ctx: commands.Context, *, roles: RoleSyntaxConverter):
        """
        adds/removes roles to all users.

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole all +RoleToGive, -RoleToRemove
        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in ctx.guild.members:
            await self.update_roles_atomically(
                member, give=roles["+"], remove=roles["-"]
            )

        await ctx.tick()

    @drole.command(name="humans")
    async def mrole_humans(self, ctx: commands.Context, *, roles: RoleSyntaxConverter):
        """
        adds/removes roles to all humans.

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole humans +RoleToGive, -RoleToRemove

        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in ctx.guild.members:
            if not member.bot:
                await self.update_roles_atomically(
                    member, give=roles["+"], remove=roles["-"]
                )

        await ctx.tick()

    @drole.command(name="user")
    async def mrole_user(
        self, ctx: commands.Context, user: discord.Member, *, roles: RoleSyntaxConverter
    ):
        """
        adds/removes roles to a user

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole user Sinbad#0001 +RoleToGive, -RoleToRemove

        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        await self.update_roles_atomically(user, give=roles["+"], remove=roles["-"])

        await ctx.tick()

    @drole.command(name="in")
    async def mrole_user(
        self, ctx: commands.Context, role: discord.Role, *, roles: RoleSyntaxConverter
    ):
        """
        adds/removes roles to all users with a specified role

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole in "Red Team" +Champions, -Losers
        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in role.members:
            await self.update_roles_atomically(
                member, give=roles["+"], remove=roles["-"]
            )

        await ctx.tick()

    @mrole.command(name="search")
    async def mrole_search(self, ctx: commands.Context, *, query: ComplexSearchConverter):
        """
        Searches for users with the specified role criteria

        --has-all roles
        --has-none roles
        --has-any roles
        --only-humans
        --only-bots
        --csv

        csv output will be used if output would exceed embed limits, or if flag is provided
        """

        members = set(ctx.guild.members)

        if not query["everyone"]:

            if query["bots"]:
                members = {m for m in members if m.bot}
            elif query["humans"]:
                members = {m for m in members if not m.bot}

            for role in query["all"]:
                members &= set(role.members)
            for role in query["none"]:
                members -= set(role.members)

            if query["any"]:
                any_union = set()
                for role in query["any"]:
                    any_union |= set(role.members)
                members &= any_union

        if len(members) < 50 and not query['csv']:

            def chunker(memberset, size=3):
                ret_str = ""
                for i, m in enumerate(memberset, 1):
                    ret_str += m.mention
                    if i % size == 0:
                        ret_str += "\n"
                    else:
                        ret_str += " "
                return ret_str

            description = chunker(members)
            color = ctx.guild.me.color if ctx.guild else discord.Embed.Empty
            embed = discord.Embed(description=description, color=color)
            await ctx.send(embed=embed, content=f"Search results for {ctx.author.mention}")

        else:
            csvf = io.StringIO()
            fieldnames = ['ID', 'Display Name', 'Username#Discrim', 'Joined Server', 'Joined Discord']
            fmt = "%Y-%m-%d"
            writer = csv.DictWriter(csvf, fieldnames=fieldnames)
            writer.writeheader()
            for member in members:
                writer.writerow(
                    {
                        'ID': member.id,
                        'Display Name': member.display_name,
                        'Username#Discrim': str(member),
                        'Joined Server': member.joined_at.strftime(fmt),
                        'Joined Discord': member.created_at.strftime(fmt),
                    }
                )

            csvf.seek(0)
            data = io.BytesIO(csvf.read().encode())
            data.seek(0)
            await ctx.send(
                content=f"Data for {ctx.author.mention}",
                files=[discord.File(data, filename=f"{ctx.message.id.csc}")],
            )
            csvf.close()
            data.close()
            del csvf
            del data

    @mrole.command(name="modify", hidden=True)
    async def mrole_complex(
        self, ctx: commands.Context, *, query: ComplexActionConverter
    ):
        """
        Basic flags...
        
        --has-all roles
        --has-none roles
        --has-any roles
        --add roles
        --remove roles
        --only-humans
        --only-bots
        --everyone
        """

        apply = {"+": query["add"], "-": query["remove"]}
        if not self.all_are_valid_roles(ctx, apply):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        members = set(ctx.guild.members)

        if not query["everyone"]:

            if query["bots"]:
                members = {m for m in members if m.bot}
            elif query["humans"]:
                members = {m for m in members if not m.bot}

            for role in query["all"]:
                members &= set(role.members)
            for role in query["none"]:
                members -= set(role.members)

            if query["any"]:
                any_union = set()
                for role in query["any"]:
                    any_union |= set(role.members)
                members &= any_union

        for member in members:
            await self.update_roles_atomically(
                member, give=query["add"], remove=query["remove"]
            )

        await ctx.tick()
