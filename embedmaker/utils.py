import discord
from redbot.core import RedContext
from redbot.core.utils.chat_formatting import box
# get rid of this if PR red#1558 is merged


async def send(ctx: RedContext, content: str) -> discord.Message:
    if await ctx.embed_requested():
        return await ctx.send(embed=discord.Embed(description=content))
    else:
        return await ctx.send(box(content))
