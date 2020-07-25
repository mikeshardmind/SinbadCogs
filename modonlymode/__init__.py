from .core import ModOnlyMode

__end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


async def setup(bot):
    await ModOnlyMode.setup(bot)
