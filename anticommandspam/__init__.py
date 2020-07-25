from redbot.core.bot import Red

from .core import AntiCommandSpam

__end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users. "
    "Discord IDs of users may occasionaly be logged to file "
    "as part of exception logging."
)


async def setup(bot: Red):
    await AntiCommandSpam.setup(bot)
