import csv
import io
import logging
from typing import Optional, cast, no_type_check, Set

import discord
from redbot.core import checks, commands

from .abc import MixinMeta
from .converters import (
    RoleSyntaxConverter,
    ComplexActionConverter,
    ComplexSearchConverter,
)
from .exceptions import RoleManagementException

log = logging.getLogger("red.sinbadcogs.rolemanagement.massmanager")


class MassManagementMixin(MixinMeta):
    """
    Mass role operations
    """

    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.group(name="massrole", autohelp=True, aliases=["mrole"])
    async def mrole(self, ctx: commands.Context):
        """
        Commands for mass role management
        """
        pass

    @staticmethod
    def search_filter(members: set, query: dict) -> set:
        """
        Reusable
        """

        if query["everyone"]:
            return members

        all_set: Set[discord.Member] = set()
        if query["all"]:
            first, *rest = query["all"]
            all_set = set(first.members)
            for other_role in rest:
                all_set &= set(other_role.members)

        none_set: Set[discord.Member] = set()
        if query["none"]:
            for role in query["none"]:
                none_set.update(role.members)

        any_set: Set[discord.Member] = set()
        if query["any"]:
            for role in query["any"]:
                any_set.update(role.members)

        minimum_perms: Optional[discord.Permissions] = None
        if query["hasperm"]:
            minimum_perms = discord.Permissions()
            minimum_perms.update(**{x: True for x in query["hasperm"]})

        def mfilter(m: discord.Member) -> bool:
            if query["bots"] and not m.bot:
                return False

            if query["humans"] and m.bot:
                return False

            if query["any"] and m not in any_set:
                return False

            if query["all"] and m not in all_set:
                return False

            if query["none"] and m in none_set:
                return False

            if query["hasperm"] and not m.guild_permissions.is_superset(minimum_perms):
                return False

            if query["anyperm"] and not any(
                bool(value and perm in query["anyperm"])
                for perm, value in iter(m.guild_permissions)
            ):
                return False

            if query["notperm"] and any(
                bool(value and perm in query["notperm"])
                for perm, value in iter(m.guild_permissions)
            ):
                return False

            if query["noroles"] and len(m.roles) != 1:
                return False

            # 0 is a valid option for these, everyone role not counted
            if query["quantity"] is not None and len(m.roles) - 1 != query["quantity"]:
                return False

            if query["lt"] is not None and len(m.roles) - 1 >= query["lt"]:
                return False

            if query["gt"] is not None and len(m.roles) - 1 <= query["gt"]:
                return False

            if query["above"] and m.top_role <= query["above"]:
                return False

            if query["below"] and m.top_role >= query["below"]:
                return False

            return True

        members = {m for m in members if mfilter(m)}

        return members

    @mrole.command(name="user")
    @no_type_check
    async def mrole_user(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        roles: RoleSyntaxConverter,
    ) -> None:
        """
        adds/removes roles to one or more users

        You cannot add and remove the same role

        Example Usage:

        [p]massrole user Sinbad --add RoleToGive "Role with spaces to give" 
        --remove RoleToRemove "some other role to remove" Somethirdrole

        [p]massrole user LoudMouthedUser ProfaneUser --add muted

        For role operations based on role membership, permissions had, or whether someone is a bot
        (or even just add to/remove from all) see `[p]massrole search` and `[p]massrole modify` 
        """
        roles = cast(dict, roles)
        give, remove = roles["add"], roles["remove"]
        apply = give + remove
        if not await self.all_are_valid_roles(ctx, *apply):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for user in users:
            await self.update_roles_atomically(who=user, give=give, remove=remove)

        await ctx.tick()

    @mrole.command(name="search")
    @no_type_check
    async def mrole_search(
        self, ctx: commands.Context, *, query: ComplexSearchConverter
    ):
        """
        Searches for users with the specified role criteria

        --has-all roles
        --has-none roles
        --has-any roles

        --has-no-roles
        --has-exactly-nroles number
        --has-more-than-nroles number
        --has-less-than-nroles number

        --has-perm permissions
        --any-perm permissions
        --not-perm permissions

        --above role
        --below role

        --only-humans
        --only-bots
        --everyone

        --csv

        csv output will be used if output would exceed embed limits, or if flag is provided
        """

        members = set(ctx.guild.members)
        query = cast(dict, query)
        members = self.search_filter(members, query)

        if len(members) < 50 and not query["csv"]:

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
            await ctx.send(
                embed=embed, content=f"Search results for {ctx.author.mention}"
            )

        else:
            await self.send_maybe_chunked_csv(ctx, list(members))

    @staticmethod
    async def send_maybe_chunked_csv(ctx: commands.Context, members):
        chunk_size = 75000
        chunks = [
            members[i : (i + chunk_size)] for i in range(0, len(members), chunk_size)
        ]

        for part, chunk in enumerate(chunks, 1):

            csvf = io.StringIO()
            fieldnames = [
                "ID",
                "Display Name",
                "Username#Discrim",
                "Joined Server",
                "Joined Discord",
            ]
            fmt = "%Y-%m-%d"
            writer = csv.DictWriter(csvf, fieldnames=fieldnames)
            writer.writeheader()
            for member in chunk:
                writer.writerow(
                    {
                        "ID": member.id,
                        "Display Name": member.display_name,
                        "Username#Discrim": str(member),
                        "Joined Server": member.joined_at.strftime(fmt)
                        if member.joined_at
                        else None,
                        "Joined Discord": member.created_at.strftime(fmt),
                    }
                )

            csvf.seek(0)
            b_data = csvf.read().encode()
            data = io.BytesIO(b_data)
            data.seek(0)
            filename = f"{ctx.message.id}"
            if len(chunks) > 1:
                filename += f"-part{part}"
            filename += ".csv"
            await ctx.send(
                content=f"Data for {ctx.author.mention}",
                files=[discord.File(data, filename=filename)],
            )
            csvf.close()
            data.close()
            del csvf
            del data

    @mrole.command(name="modify")
    async def mrole_complex(
        self, ctx: commands.Context, *, query: ComplexActionConverter
    ):
        """
        Similar syntax to search, while applying/removing roles
        
        --has-all roles
        --has-none roles
        --has-any roles

        --has-no-roles
        --has-exactly-nroles number
        --has-more-than-nroles number
        --has-less-than-nroles number

        --has-perm permissions
        --any-perm permissions
        --not-perm permissions

        --above role
        --below role

        --only-humans
        --only-bots
        --everyone
        
        --add roles
        --remove roles
        """
        query = cast(dict, query)
        apply = query["add"] + query["remove"]
        if not await self.all_are_valid_roles(ctx, *apply):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        members = set(ctx.guild.members)
        members = self.search_filter(members, query)

        if len(members) > 100:
            await ctx.send(
                "This may take a while given the number of members to update."
            )

        async with ctx.typing():
            for member in members:
                try:
                    await self.update_roles_atomically(
                        who=member, give=query["add"], remove=query["remove"]
                    )
                except RoleManagementException:
                    log.debug(
                        "Internal filter failure on member id %d guild id %d query %s",
                        member.id,
                        ctx.guild.id,
                        query,
                    )
                except discord.HTTPException:
                    log.debug(
                        "Unpredicted failure for member id %d in guild id %d query %s",
                        member.id,
                        ctx.guild.id,
                        query,
                    )

        await ctx.tick()
