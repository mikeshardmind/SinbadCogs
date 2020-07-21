import contextlib

import discord
from redbot.core import commands


async def before_invoke_hook(ctx: commands.Context):
    guild = ctx.guild
    if not guild:
        return

    if guild.me == guild.owner:
        return

    if await ctx.bot.is_owner(guild.owner):
        return

    author, me = ctx.author, guild.me
    assert isinstance(author, discord.Member)  # nosec

    if me.guild_permissions.administrator:
        if (
            author.top_role > me.top_role or author == guild.owner
        ) and author.guild_permissions.manage_roles:
            with contextlib.suppress(Exception):
                await ctx.send(
                    "This bot refuses to work with admin permissions. "
                    "They are dangerous and lazy to give out."
                )

        raise commands.CheckFailure()


def setup(bot):
    bot.before_invoke(before_invoke_hook)


def teardown(bot):
    bot.remove_before_invoke_hook(before_invoke_hook)
