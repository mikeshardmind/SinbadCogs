import contextlib

import discord
from redbot.core import commands

__red_end_user_data_statement__ = (
    "This extension does not persistently store data or metadata about users."
)


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


async def setup(bot):
    await bot.send_to_owners(
        "This cog still functions, but I suggest you leave and stop using Red. "
        "I was removed from Red for not wanting my work misrepresented by the "
        "organization, and stating what I would do *if* that continued. "
        'For how much Red and it\'s members go after people who " take credit" '
        "for their work, they sure were quick to dismiss mine. "
        "The cog will recieve no further updates, nor is anyone legally allowed to fork to update."
    )
    bot.before_invoke(before_invoke_hook)


def teardown(bot):
    bot.remove_before_invoke_hook(before_invoke_hook)
