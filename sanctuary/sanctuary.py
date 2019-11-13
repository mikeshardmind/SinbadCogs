import asyncio
import csv
import io
import logging

from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

import discord

from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.mod import slow_deletion, mass_purge
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("red.sinbadcogs.sanctuary")


class TimeParser:
    def __init__(self, td):
        self.td: timedelta = td

    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str):
        maybe_td = commands.parse_timedelta(argument=arg)
        if not maybe_td:
            raise commands.BadArgument()
        return cls(maybe_td)


class Sanctuary(commands.Cog):
    """ Cogs for Sancturary """

    def __init__(self, bot):
        self.bot = bot

    @checks.mod()
    @checks.bot_has_permissions(read_message_history=True)
    @commands.command()
    async def getinactives(self, ctx, *, amountoftime: TimeParser):
        """
        Get the inactive users.

        "amountoftime" can be something like 90 days.
        """

        await ctx.send("This may take a while...")

        delta = amountoftime.td
        post = ctx.message.created_at - delta

        full_counts: Dict[int, int] = defaultdict(int)
        full_recents: Dict[int, datetime] = defaultdict(
            lambda: datetime.utcfromtimestamp(0)
        )

        vals = await asyncio.gather(
            *[self.count_channel(c) for c in ctx.guild.text_channels]
        )

        for counts, most_recents in vals:
            for idx, count in counts.items():
                full_counts[idx] += count
            for idx, most_recent in most_recents.items():
                full_recents[idx] = max(full_recents[idx], most_recent)

        recents, counts, members = {}, {}, []
        default_time = datetime.utcfromtimestamp(0)
        for user_id, most_recent in full_recents.items():
            if most_recent < post:
                m = ctx.guild.get_member(user_id)
                if m:
                    recents[m] = most_recent if most_recent != default_time else None
                    counts[m] = full_counts[m.id]
                    members.append(m)

        await self.send_maybe_chunked_csv(ctx, members, recents, counts)

    @staticmethod
    async def count_channel(
        chan: discord.TextChannel
    ) -> Tuple[Dict[int, int], Dict[int, datetime]]:

        counts: Dict[int, int] = defaultdict(int)
        recents: Dict[int, datetime] = defaultdict(lambda: datetime.utcfromtimestamp(0))

        try:
            async for message in chan.history(limit=None):
                aid = message.author.id
                counts[aid] += 1
                recents[aid] = max(recents[aid], message.created_at)
        finally:
            return counts, recents

    @staticmethod
    async def send_maybe_chunked_csv(ctx: commands.Context, members, recents, counts):
        if not members:
            return await ctx.send("Zero matches.")

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
                        "Last Message": recents[member.id],
                        "Total Messages": counts[member.id],
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

    @commands.check(lambda ctx: ctx.channel.id == 558046096790913055)
    @checks.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.guild_only()
    @checks.mod()
    @commands.command()
    async def removegone(self, ctx: commands.Context):
        """
        Removes posts from users no longer in the channel
        """
        await ctx.send(
            f"Are you sure you want to remove all messages "
            f"from people not currently able to read this channel? (yes/no)"
        )
        try:
            response = await ctx.bot.wait_for(
                "message", check=MessagePredicate.same_context(ctx), timeout=30.0
            )
        except asyncio.TimeoutError:
            await ctx.send("Took too long to respond...")
            return

        if response.content.lower() != "yes":
            await ctx.send("Okay, try again later.")
            return

        safe_ids = [m.id for m in ctx.channel.members]
        bulk = []
        old = []

        then = ctx.message.created_at - timedelta(days=13, hours=6)

        try:
            async with ctx.typing():
                async for m in ctx.history(limit=None):
                    if m.author.id in safe_ids:
                        continue

                    if m.created_at > then:
                        bulk.append(m)
                    else:
                        old.append(m)

                await mass_purge(bulk, ctx.channel)
                await slow_deletion(old)
        except discord.Forbidden as exc:
            await ctx.send("I seem to be missing permissions to do that.")
        except discord.HTTPException as exc:
            log.exception("Error in removegone")
            await ctx.send("Something went wrong, contact the bot owner...")
        else:
            await ctx.tick()
