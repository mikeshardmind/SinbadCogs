from redbot.core import commands, checks
from redbot.core.config import Config


class AudioHook:

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "0.0.1a"
    __flavor__ = "hard-coded bullshit, not suited for general use yet."

#    def __init__(self, bot):
#        self.bot= bot
#        self.config = Config.get_conf(self, 78631113035100160, force_registration=True)
#        self.config.register_global(allowed=[], associated_allows=[])

    async def __permission_hook(self, ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        
        if ctx.cog.__class__.__name__ != "Audio":
            return None

        if not ctx.guild:
            return None

        return ctx.guild.get_member(78631113035100160) is not None
