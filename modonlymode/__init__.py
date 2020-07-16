from .core import ModOnlyMode


async def setup(bot):
    await ModOnlyMode.setup(bot)
