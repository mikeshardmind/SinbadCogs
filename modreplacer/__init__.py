from redbot.core.bot import Red
from .mod import Mod


async def setup(bot: Red):
    await bot.get_cog("Core")._unload("Mod")
    bot.add_cog(Mod(bot))
