import asyncio
import contextlib
from uuid import getnode

import discord
from redbot.core import commands, config
from redbot.core.bot import Red

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
    asyncio.create_task(maybe_send_owners(bot))
    bot.before_invoke(before_invoke_hook)


def teardown(bot):
    bot.remove_before_invoke_hook(before_invoke_hook)


async def maybe_send_owners(bot: Red):
    # I have been provided multiple reasons to do it this way and not disable this completely.
    # You can thank someone reaching out and having a discussion about this and a balance
    # between not allowing issues being covered up or to be easily by passed up and not
    # stranding users with no other options in the immediate term. (the reason I didn't just fundamentally break the cogs)
    # This can still be circumvented, but that would be removing license information conveyed to end users.
    await bot.wait_until_red_ready()
    node_id = getnode()

    conf = config.Config.get_conf(
        None, identifier=node_id, cog_name=f"SinbadCogs-{node_id}"
    )

    conf.register_global(last_notify=[])

    async with conf.last_notify.get_lock():
        last_notify = await conf.last_notify()
        cur_uptime = list(bot.uptime.timetuple()[:6])
        if last_notify is None or cur_uptime > last_notify:

            await bot.send_to_owners(
                "This cog still functions, but I suggest you stop using Red and find an "
                "alternative that cares about the contributions of volunteers or pays their devs. "
                "I was removed from Red for not wanting my work misrepresented by the "
                "organization, and stating what I would do *if* that continued. "
                'For how much Red and it\'s members go after people who "take credit" '
                "for their work, they sure were quick to dismiss mine. "
                "The cog will likely recieve no further updates, nor does the license "
                "(which can be found here: <https://github.com/mikeshardmind/SinbadCogs/blob/v3/LICENSE>) "
                "permit public modifications by third parties."
                "\nThis message was provided by a cog in <https://github.com/mikeshardmind/SinbadCogs/> "
                "and an attempt will be made not to resend this message before the next bot restart."
            )
            await conf.last_notify.set(cur_uptime)
