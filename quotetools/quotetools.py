from typing import Any
from redbot.core import commands
import discord
from .helpers import find_messages, embed_from_msg

Base: Any = getattr(commands, "Cog", object)


class QuoteTools(commands.Cog):
    """
    Cog for quoting messages by ID
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "1.3.0"
    __flavor_text__ = "Message jump links are go"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @commands.command()
    async def quote(
        self,
        ctx,
        channels: commands.Greedy[discord.TextChannel] = None,
        *messageids: int
    ):
        """
        gets (a) message(s) by ID(s)

        User must be able to see the message(s)

        You can optionally limit search to specific channels to speed things up
        """

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
