from redbot.core import commands


def can_mention_here():
    async def check(ctx: commands.Context):
        if not ctx.guild:
            return False
        cog = ctx.bot.get_cog("RoleMentions")
        if not cog:
            return False
        return await cog.config.channel(ctx.channel).mentions_here()

    return commands.check(check)
