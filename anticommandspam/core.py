import logging
from collections import Counter
from typing import MutableMapping

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify

log = logging.getLogger("red.sinbadcogs.anticommandspam")


class AntiCommandSpam(commands.Cog):
    """
    Blocks users who spam commands from
    interacting with the bot until next reboot
    """

    __version__ = "0.0.2a"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.blocked = discord.utils.SnowflakeList(())
        self.cooldown = commands.CooldownMapping.from_cooldown(
            6, 12, commands.BucketType.user
        )
        self.consecutive_cooldowns: MutableMapping[int, int] = Counter()

    async def custom_before_invoke(self, ctx: commands.Context):

        if await ctx.bot.is_owner(ctx.author):
            return

        retry_time = self.cooldown.update_rate_limit(ctx.message)

        author_id = ctx.author.id

        if retry_time:
            self.consecutive_cooldowns[author_id] += 1
            if self.consecutive_cooldowns[author_id] > 3:
                if not self.blocked.has(author_id):
                    self.blocked.add(author_id)
                log.info(
                    "User: {user_id} has been blocked until next "
                    "cog load for 4 consecutive global cooldown hits",
                    user_id=author_id,
                )

            raise commands.CheckFailure("I don't like spam.")

        else:

            self.consecutive_cooldowns.pop(author_id, None)

    async def custom_check_once(self, ctx: commands.Context):
        return not self.blocked.has(ctx.author.id)

    @classmethod
    async def setup(cls, bot: Red):
        c = cls(bot)
        bot.add_cog(c)
        bot.add_check(c.custom_check_once, call_once=True)
        bot.before_invoke(c.custom_before_invoke)

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.custom_before_invoke)
        self.bot.remove_check(self.custom_check_once, call_once=False)

    @checks.is_owner()
    @commands.group()
    async def anticommandspam(self, ctx: commands.Context):
        """ Commands for AntiCommandSpam """
        pass

    @anticommandspam.command(name="list")
    async def acs_list(self, ctx: commands.Context):
        """ Get a list of users currently blocked for spamming """

        if not self.blocked:
            return await ctx.send("Nobody blocked right now.")

        message = " ".join(f"<@!{idx}>" for idx in self.blocked)

        r = discord.http.Route(
            "POST", "/channels/{channel_id}/messages", channel_id=ctx.channel.id,
        )

        for page in pagify(message):

            kwargs = {
                "allowed_mentions": {"parse": []},
                "content": page,
            }
            await self.bot.http.request(r, json=kwargs)  # type: ignore

    @anticommandspam.command(name="clear")
    async def acs_clear(self, ctx: commands.Context):
        """ Clear the currrent spam list """
        self.blocked = discord.utils.SnowflakeList(())
        await ctx.tick()

    @anticommandspam.command(name="remove")
    async def acs_remove(self, ctx: commands.Context, user_id: int):
        """ Remove a user id from the spam list """
        if self.blocked.has(user_id):
            self.blocked.remove(user_id)
            await ctx.tick()
        else:
            await ctx.send("User was not in the spam list")
