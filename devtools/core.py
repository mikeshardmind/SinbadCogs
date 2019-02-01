import asyncio
import re
import unicodedata as ud


import discord
from redbot.core import commands, checks

SPOILER_RE = re.compile(r"(?s)\|{2}(?P<CONTENT>.*?)\|{2}")


class DevTools(commands.Cog):
    """ Some tools """

    __author__ = "mikeshardmind"
    __version__ = "1.0.1"
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


    @checks.admin_or_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.command()
    async def unspoil(self, ctx, message_id):
        """ Get what was said without spoiler tags """

        message = discord.utils.get(ctx.guild._state._messages, channel=ctx.channel, id=message_id)
        if message is None:
            try:
                message = await ctx.channel.get_message(message_id)
            except discord.NotFound:
                return await ctx.send("No such message")
            except discord.Forbidden:
                return await ctx.send("I don't have permissions for message history")
            except discord.HTTPException as exc:
                return await ctx.send(f"Something went wrong there: {type(exc)}")

        text = SPOILER_RE.sub(r"\g<CONTENT>", message.content)
        text = text.strip()
        if text:
            await ctx.send(text)        
