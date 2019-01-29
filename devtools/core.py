import asyncio
import discord
import unicodedata as ud
from redbot.core import commands


class DevTools(commands.Cog):
    """ Some tools """

    __author__ = "mikeshardmind"
    __version__ = "1.0.0"
    __flavor_text__ = "Stuff"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="emojiinfo")
    async def emoji(self, ctx):
        """
        Find info about an emoji
        """
        m = await ctx.send("React with the emoji you want info about")

        try:
            react: discord.Reaction
            react, _user = await ctx.bot.wait_for(
                "reaction_add",
                check=(lambda r, u: u == ctx.author and r.message.id == m.id),
                timeout=60,
            )
        except asyncio.TimeoutError:
            return await ctx.send("Okay, try again later.")
        else:
            emoji = react.emoji

        if isinstance(emoji, str):
            open_b, close_b = "{", "}"
            to_send = "".join(f"\\N{open_b}{ud.name(c)}{close_b}" for c in emoji)
            e_type = "unicode"
        else:
            to_send = str(emoji)
            e_type = "custom"

        await ctx.send(
            f"To send or react with this {e_type} emoji, send or react with:"
            f'\n```\n"{to_send}"\n```'
        )
