import asyncio
import contextlib
import re
from copy import copy
import unicodedata as ud
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import box, pagify
import discord
from redbot.core import commands, checks

SPOILER_RE = re.compile(r"(?s)\|{2}(?P<CONTENT>.*?)\|{2}")


class DevTools(commands.Cog):
    """ Some tools """

    __version__ = "2.0.2"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="userallowedcoms")
    async def usercontextallowedcoms(self, ctx, *, member: discord.Member):
        """ checks user allowed commands in context """

        fmsg = copy(ctx.message)
        fmsg.author = member
        fctx = await ctx.bot.get_context(fmsg)

        async def can_run_filter(a_context, coms):
            for com in coms:
                with contextlib.suppress(Exception):
                    if await com.can_run(a_context, check_all_parents=True):
                        return True

        coms = [
            c.qualified_name
            for c in ctx.bot.walk_commands()
            if await can_run_filter(fctx, *ctx.bot.commands)
        ]
        coms.sort()
        out = ", ".join(coms)
        pages = [box(p) for p in pagify(out)]
        if not pages:
            await ctx.send("They can't run anything here")
        elif len(pages) == 1:
            await ctx.send(pages[0])
        else:
            await menus.menu(ctx, pages, menus.DEFAULT_CONTROLS)

    @commands.command(name="emojiinfo")
    async def emoji(self, ctx):
        """
        Find info about an emoji
        """
        m = await ctx.send("React with the emoji you want info about")

        try:
            react, _user = await ctx.bot.wait_for(
                "reaction_add",
                check=(lambda r, u: u == ctx.author and r.message.id == m.id),
                timeout=60,
            )  # type: discord.Reaction, discord.User
        except asyncio.TimeoutError:
            return await ctx.send("Okay, try again later.")
        else:
            emoji = react.emoji

        if isinstance(emoji, str):
            open_b, close_b = "{", "}"
            to_send = "".join(f"\\N{open_b}{ud.name(c)}{close_b}" for c in emoji)
            await ctx.send(
                f"To send or react with this unicode emoji, send or react with:"
                f'\n```\n"{to_send}"\n```'
            )
        else:
            await ctx.send(
                f"This is a custom emoji. To send it or react with it, "
                f"you can get the emoji object and send it or react with it. "
                f"Bots don't need nitro, but do need the emote to use it. Example: "
                f"\n```py\n"
                f"emoji = discord.utils.get(bot.emojis, id={emoji.id})\n"
                f"# This is the id of the emoji you reacted with\n"
                f"if emoji:\n"
                f'    await ctx.send("Some string {{}}".format(emoji))\n'
                f"    await ctx.message.add_reaction(emoji)\n"
                f"else:\n"
                f'    await ctx.send("I can\'t use that emoji")\n```'
            )

    # noinspection PyProtectedMember
    @checks.admin_or_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.command()
    async def unspoil(self, ctx, message_id: int):
        """ Get what was said without spoiler tags """

        message = discord.utils.get(
            ctx.guild._state._messages, channel=ctx.channel, id=message_id
        )
        if message is None:
            try:
                try:
                    message = await ctx.channel.fetch_message(message_id)
                except AttributeError:
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
