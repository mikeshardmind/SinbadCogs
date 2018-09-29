from typing import Any
from redbot.core import commands

from .helpers import find_msg, embed_from_msg

Base: Any = getattr(commands, "Cog", object)


class QuoteTools(Base):
    """
    Cog for quoting messages by ID
    """

    __author__ = "mikeshardmind(Sinbad#0001)"
    __version__ = "1.1.2"

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def quote(self, ctx, *messageid: int):
        """
        gets (a) message(s) by ID(s)

        User must be able to see the message(s)
        """

        msgs = [await find_msg(ctx=ctx, idx=idx) for idx in messageid]
        msgs = [m for m in msgs if m]
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
                        "Time(UTC): {}".format(m.timestamp.isoformat()),
                    ]
                )
                if len(msg1) + len(m.clean_content) < 2000:
                    await ctx.send(msg1 + m.clean_content)
                else:
                    await ctx.send(msg1)
                    await ctx.send(m.clean_content)
