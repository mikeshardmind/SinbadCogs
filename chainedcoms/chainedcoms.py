import logging
from copy import copy

import discord
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

        commands will run in order, stopping at the first errored command
        in the chain.

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

    @commands.command()
    async def chaincom_targeted(self, ctx: RedContext, delim: str,
                                target: discord.User, *coms: str):
        """
        works like chaincom, but also allows a target parameter
        for use with alias

        target should be swapped in as needed using {target}
        """
        await self._chain_com_process(
            ctx=ctx,
            delim=delim,
            target=target.mention,
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
                author=ctx.author,
                target=target
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
                break
            else:
                log.debug(m.content)
        else:
            await ctx.tick()
