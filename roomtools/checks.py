from redbot.core import commands


def tmpc_active():
    async def check(ctx: commands.Context):
        if not ctx.guild:
            return False
        cog = ctx.bot.get_cog("TempChannels")
        if not cog:
            return False
        return await cog.config.guild(ctx.guild).active()

    return commands.check(check)


def aa_active():
    async def check(ctx: commands.Context):
        if not ctx.guild:
            return False
        cog = ctx.bot.get_cog("AutoRooms")
        if not cog:
            return False
        return await cog.config.guild(ctx.guild).active()

    return commands.check(check)
