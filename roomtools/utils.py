from redbot.core import RedContext
import discord


async def send(ctx: RedContext, content: str):
    if await ctx.embed_requested():
        return await ctx.send(embed=discord.Embed(description=content))
    else:
        return await ctx.send(content)
