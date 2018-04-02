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
    async def chaincom(self, ctx: RedContext, delim: str, *coms: str):
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
                                target: str, *coms: str):
        """
        works like chaincom, but also allows a target parameter
        for use with alias

        target should be swapped in as needed using {target}
        """
        await self._chain_com_process(
            ctx=ctx,
            delim=delim,
            target=target,
            coms=coms
        )

    async def _chain_com_process(
        self, *, ctx: RedContext, delim: str,
            target: str=None, coms: str):
        """ heavy lifting here """

        actions = coms.format(
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            target=target
        ).split(delim)

        self.queues[ctx.message.id] = {
            'real_ctx': ctx,
            'original_content': copy(ctx.message.content),
            'actions': actions
        }

    async def on_command_completion(self, ctx: RedContext):
        """
        Where the magic happens
        """

        if ctx.message.id in self.queues:
            qinfo = self.queues[ctx.message.id]
            if qinfo['actions']:
                m = copy(ctx.message)
                m.content = "{}{}".format(
                    ctx.prefix, qinfo['actions'].pop(0)
                )
                forged_ctx = await ctx.bot.get_context(m, cls=RedContext)
                try:
                    await ctx.bot.invoke(forged_ctx)
                except Exception as e:
                    log.exception(e)
                    self.queues.pop(ctx.message.id, None)
                else:
                    log.debug(m.content)
            else:
                await qinfo['real_ctx'].tick()
                self.queues.pop(ctx.message.id, None)
