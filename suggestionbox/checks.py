from redbot.core import commands


def has_active_box():
    async def check(ctx: commands.Context):
        if not ctx.guild:
            return False
        cog = ctx.bot.get_cog("SuggestionBox")
        if not cog:
            return False
        return bool(await cog.config.guild(ctx.guild).boxes())

    return commands.check(check)