import functools
import sys

from discord.ext import commands

from redbot.core.bot import Red, RedContext
# from redbot.core import checks
from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import pagify

from .jailer import run_jailed

_ = CogI18n('Calculator', __file__)


class Calculator:
    """
    This provides a safe(er) method for allowing math
    to be evaluated by the bot.

    This utilizes asteval paired with resource limited subproccesses

    This should be safe for use on linux.
    I am preventing use of it on other platforms
    due to lack of testing and confidence it would be safe there.
    """

    __author__ = "mikeshardmind"
    __version__ = '0.0.1a'

    def __init__(self, bot: Red):
        self.bot = bot

    def __local_check(self, ctx):
        return sys.platform == 'linux'

    @commands.command(name='calc', aliases=['calculate'])
    async def calculate(self, ctx: RedContext, *, expression: str=""):
        """
        get the result of an expression

        a few predefined values exist for your convienience:

        e: e
        pi: pi
        gamma: Eueler's constant

        libs imported and available for use:
        numpy
        math
        """

        if not expression:
            return await ctx.send_help()
        await self.run_calc(ctx)

    async def run_calc(self, ctx: RedContext):
        wrapped = self._wrap(ctx)
        x = await self.bot.loop.run_in_executor(None, wrapped)
        x.add_done_callback(functools.partial(self._callback, ctx=ctx))

    def _wrap(self, ctx: RedContext):
        return functools.partial(
            run_jailed,
            expr=ctx.message.content,
            ctx=ctx
        )

    def _callback(self, fn, *, ctx: RedContext):
        self.bot.loop.schedule_task(
            self._respond(ctx, fn.result())
        )

    async def _respond(self, ctx: RedContext, resp: str):

        if resp is None:
            message = _(
                'An error occurred parsing your calculation '
                'or your calculation time exceeded the limits')
        else:
            message = _(
                'Result for expression:\n'
                '```py\n{formula}\n```\n\n'
                '```\n{result}\n```').format(formula=ctx.content, result=resp)

        for page in pagify(message):
            await ctx.send(message)
