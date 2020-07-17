from __future__ import annotations

import re
from typing import NamedTuple

import discord
from redbot.core import commands

from .helpers import embed_from_msg, find_messages

CHANNEL_RE = re.compile(r"^<#(\d{15,21})>$|^(\d{15,21})$")


class GlobalTextChannel(NamedTuple):
    matched_channel: discord.TextChannel

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str):

        bot = ctx.bot

        match = CHANNEL_RE.match(argument)
        channel = None
        if match:
            idx = next(filter(None, match.groups()), None)

            if idx:
                channel_id = int(idx)
                channel = bot.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.TextChannel):
            raise commands.BadArgument('Channel "{}" not found.'.format(argument))

        return cls(channel)


class QuoteTools(commands.Cog):
    """
    Cog for quoting messages by ID
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "339.1.0"

    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @commands.command()
    async def quote(
        self, ctx, channels: commands.Greedy[GlobalTextChannel] = None, *messageids: int
    ):
        """
        gets (a) message(s) by ID(s)

        User must be able to see the message(s)

        You need to specify specific channels to search (by ID or mention only!)
        """

        if not messageids or not channels:
            return await ctx.send_help()

        chans = [c.matched_channel for c in channels]

        msgs = await find_messages(ctx, messageids, chans)
        if not msgs:
            return await ctx.maybe_send_embed("No matching message found.")

        for m in msgs:
            if await ctx.embed_requested():
                em = embed_from_msg(m)
                await ctx.send(embed=em)
            else:
                msg1 = "\n".join(
                    [
                        f"Author: {m.author}({m.author.id})",
                        f"Channel: <#{m.channel.id}>",
                        f"Time(UTC): {m.created_at.isoformat()}",
                    ]
                )
                if len(msg1) + len(m.clean_content) < 2000:
                    await ctx.send(msg1 + m.clean_content)
                else:
                    await ctx.send(msg1)
                    await ctx.send(m.clean_content)
