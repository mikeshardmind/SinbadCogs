from __future__ import annotations

import asyncio
import contextlib
import functools
import hashlib
import re
import unicodedata as ud
from copy import copy

import discord
from redbot.core import checks, commands
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import box, pagify

from .variations import APPEND_VARIATIONS_TO

SPOILER_RE = re.compile(r"(?s)\|{2}(?P<CONTENT>.*?)\|{2}")
VARIATION = "\N{VARIATION SELECTOR-16}"


def get_name(c: str) -> str:
    """
    Gets the name of a single character,
    or the raw unicode escape is name isn't available
    """
    open_b, close_b = "{", "}"
    try:
        return f"\\N{open_b}{ud.name(c)}{close_b}"
    except ValueError:
        return c.encode("raw_unicode_escape").decode("utf-8")


class DevBase:
    @commands.guild_only()
    @commands.command(name="userallowedcoms")
    async def usercontextallowedcoms(
        self, ctx: commands.Context, *, member: discord.Member
    ):
        """ checks user allowed commands in context """

        fmsg = copy(ctx.message)
        fmsg.author = member
        fctx = await ctx.bot.get_context(fmsg)

        async def can_run_filter(a_context, com):
            with contextlib.suppress(Exception):
                if await com.can_run(a_context, check_all_parents=True):
                    return True

        coms = list(
            {
                c.qualified_name
                for c in ctx.bot.walk_commands()
                if await can_run_filter(fctx, c)
            }
        )
        coms.sort()
        out = ", ".join(coms)
        pages = [box(p) for p in pagify(out, delims=",")]
        if not pages:
            await ctx.send("They can't run anything here")
        elif len(pages) == 1:
            await ctx.send(pages[0])
        else:
            await menus.menu(ctx, pages, menus.DEFAULT_CONTROLS)

    @commands.command(name="emojiinfo")
    async def emoji(self, ctx: commands.Context):
        """
        Find info about an emoji
        """
        m = await ctx.send("React with the emoji you want info about")

        try:
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
            if emoji in APPEND_VARIATIONS_TO:
                emoji = emoji + VARIATION
            to_send = "".join(get_name(c) for c in emoji)
            await ctx.send(
                f"This is a unicode emoji. To send it or react with it, "
                f"just pass the string itself. Some emoji should use variation-selector-16 "
                f"to request an emoji rendering for consistent behavior. "
                f"\n(Further reading <https://unicode.org/Public/emoji/12.1/emoji-variation-sequences.txt>)"
                f"\nExample: "
                f"\n```py\n"
                f"# The example uses the emoji you used\n"
                f'await ctx.send("{to_send}")\n'
                f'await ctx.message.add_reaction("{to_send}")\n```'
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

    @checks.admin_or_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.command()
    async def unspoil(self, ctx: commands.Context, message_id: int):
        """ Get what was said without spoiler tags """

        message = discord.utils.get(
            ctx.bot.cached_messages, channel=ctx.channel, id=message_id
        )
        if message is None:
            try:
                message = await ctx.channel.fetch_message(message_id)
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


# Okay, so some dynamic fuckery is gonna happen here due to the
# way the discord.py metaclass works


# This needs self, as it belongs to the cog, discord.py will try to
# inject the cog instance as the first parameter.
# We don't actually need it if not for this behavior
@commands.cooldown(1, 2, commands.BucketType.user)
@commands.group(name="hashlib")
async def hashlib_command(self, ctx: commands.Context):
    """
    Hash commands
    """
    pass


for hashname in hashlib.algorithms_available:

    if "shake" in hashname:
        continue
    # not supporting it.
    # Would support if length was optional and defaulted to max

    # Meanwhile (see above about self), as this is not defined on the class at all
    # This needs to *not* have self defined

    async def callback(func_name, ctx: commands.Context, *, to_hash: str):

        hashed = hashlib.new(func_name)
        hashed.update(to_hash.encode())
        hexed = hashed.hexdigest()
        await ctx.send(box(hexed))

    # Patch this in Red... ffs
    p = functools.partial(callback, hashname)
    p.__globals__ = callback.__globals__  # type: ignore
    p.__module__ = callback.__module__

    c = commands.command(name=hashname, help=f"Hash using {hashname}")(p)

    if c.name not in hashlib_command.all_commands:
        hashlib_command.add_command(c)


class HashlibMixin:
    """ This is mostly here to easily mess with things... """

    c = hashlib_command


class DevTools(HashlibMixin, DevBase, commands.Cog):
    """
    Some tools
    """

    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )
    __version__ = "339.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
