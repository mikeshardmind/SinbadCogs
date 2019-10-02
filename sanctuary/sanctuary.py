import asyncio
import logging

from datetime import datetime, timedelta

import discord

from redbot.core import commands, checks
from redbot.core.utils.mod import slow_deletion, mass_purge
from redbot.core.utils.predicates import MessagePredicate

log = logging.getLogger("red.sinbadcogs.sanctuary")


class Sanctuary(commands.Cog):
    """ Cogs for Sancturary """

    def __init__(self, bot):
        self.bot = bot

    @checks.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.guild_only()
    @checks.mod()
    @commands.command()
    async def removegone(self, ctx: commands.Context):
        """
        Removes posts from users no longer in the channel
        """
        prompt = await ctx.send(
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
