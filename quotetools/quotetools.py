from discord.ext import commands

from .helpers import find_msg, embed_from_msg


class QuoteTools:
    """
    Cog for quoting messages by ID
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def quote(self, ctx, messageid):
        """
        gets a message by ID

        User must be able to see the message
        """

        m = await find_msg(messageid)
        if m is None:
            return await ctx.maybe_send_embed("No matching message found.")

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
