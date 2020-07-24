from redbot.core.bot import Red

from .core import AntiCommandSpam


async def setup(bot: Red):
    await AntiCommandSpam.setup(bot)
