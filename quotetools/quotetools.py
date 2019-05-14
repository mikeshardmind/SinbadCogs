from typing import Any
from redbot.core import commands
import discord
from .helpers import find_messages, embed_from_msg
import re

Base: Any = getattr(commands, "Cog", object)

CHANNEL_RE = re.compile(r"^<#(\d{15,21})>$|^(\d{15,21})$")


class GlobalChannel(commands.Converter):
    async def convert(self, ctx, argument):

        bot = ctx.bot

        match = CHANNEL_RE.match(argument)
        channel = None
        if match:
            idx = next(filter(None, match.groups()), None)

            if idx:
                channel_id = int(idx)
                channel = bot.get_channel(channel_id)

        if not channel or not isinstance(channel, discord.abc.Messageable):
            raise commands.BadArgument('Channel "{}" not found.'.format(argument))

        return channel


class QuoteTools(commands.Cog):
    """
    Cog for quoting messages by ID
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "1.3.2"
    __flavor_text__ = "Message jump links are go"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @commands.command()
    async def quote(
        self, ctx, channels: commands.Greedy[GlobalChannel] = None, *messageids: int
    ):
        """
        gets (a) message(s) by ID(s)

        User must be able to see the message(s)

        You need to specify specific channels to search (by ID or mention only!)
        (Owner is exempt from this, but it may be slow and API heavy)
        """

        if not messageids or (not channels and not await ctx.bot.is_owner(ctx.author)):
            return await ctx.send_help()

        msgs = await find_messages(ctx, messageids, channels)
        if not msgs:
            return await ctx.maybe_send_embed("No matching message found.")

        for m in msgs:
            if await ctx.embed_requested():
                em = embed_from_msg(m)
                await ctx.send(embed=em)
            else:
                msg1 = "\n".join(
                    [
                        "Author: {0}({0.id})".format(m.author),
                        "Channel: {}".format(m.channel.mention),
                        "Time(UTC): {}".format(m.created_at.isoformat()),
                    ]
                )
                if len(msg1) + len(m.clean_content) < 2000:
                    await ctx.send(msg1 + m.clean_content)
                else:
                    await ctx.send(msg1)
                    await ctx.send(m.clean_content)
