class CheckMagic:
    """
    Magical
    """

    async def __global_check(self, ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.guild and await ctx.bot.is_owner(ctx.guild.owner):
            return True
        if ctx.guild and ctx.guild.id in (240154543684321280, 133049272517001216):
            return ctx.cog.__class__.__name__ not in ("Audio",)
        return False
