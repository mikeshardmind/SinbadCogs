from redbot.core import commands


class AudioHook(commands.Cog):

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "0.0.1a"
    __flavor__ = "hard-coded bullshit, not suited for general use yet."

    def __init__(self, bot):
        self.bot = bot

    async def __global_check(self, ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True

        if ctx.cog.__class__.__name__ != "Audio":
            return True

        if not ctx.guild:
            return True

        return ctx.guild.get_member(78631113035100160) is not None
