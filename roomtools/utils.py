from redbot.core import commands
import discord


async def send(ctx: commands.Context, content: str):
    if await ctx.embed_requested():
        return await ctx.send(embed=discord.Embed(description=content))
    else:
        return await ctx.send(content)
