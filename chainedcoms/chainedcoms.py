import logging
from copy import copy

from redbot.core import RedContext
from discord.ext import commands

log = logging.getLogger('red.chainedcoms')


class ChainedComs:
    """
    Chain commands together
    """

    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    @commands.command(name="chaincom")
    async def chaincom(self, ctx: RedContext, delim: str, *, coms: str):
        """
        Specify a delimiter for commands,
        followed by each command seperated by said delimiter

        commands will be queued in order, but are not
        guaranteed to finish in order

        certain special sequences will get swapped out:
        {guild}
        {author}
        {channel}
        """
        await self._chain_com_process(
            ctx=ctx,
            delim=delim,
            coms=coms
        )

    async def _chain_com_process(
        self, *, ctx: RedContext, delim: str,
            target: str=None, coms: str):
        """ heavy lifting here """

        actions = [
            x.strip() for x in coms.format(
                guild=ctx.guild,
                channel=ctx.channel,
                author=ctx.author
            ).split(delim)
        ]

        for action in actions:
            m = copy(ctx.message)
            m.content = "{}{}".format(
                ctx.prefix, action
            )
            forged_ctx = await ctx.bot.get_context(m, cls=RedContext)
            try:
                await ctx.bot.invoke(forged_ctx)
            except Exception as e:
                log.exception(e)
            else:
                log.debug(m.content)
        else:
            await ctx.tick()
