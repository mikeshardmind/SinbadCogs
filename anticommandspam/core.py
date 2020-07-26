import asyncio
import logging
from collections import Counter
from typing import MutableMapping, Optional

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify

log = logging.getLogger("red.sinbadcogs.anticommandspam")


class AntiCommandSpam(commands.Cog):
    """
    Blocks users who spam commands from
    interacting with the bot for a while.

    This cog is still in early testing!

    TODO:
        - Add spam stats commands
        - Dynamic settings
        - Progressive Punishments for repeat offenders.
    """

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return

    __version__ = "0.0.7a"
    messages = {
        1: "Come back in another 30 seconds or so.",
        2: "I don't like spam.",
        3: "And, that's my cue to ignore you for now. Maybe try tommorow.",
        4: None,
    }

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.blocked = discord.utils.SnowflakeList(())
        self.prev_blocks = discord.utils.SnowflakeList(())
        self.cooldown = commands.CooldownMapping.from_cooldown(
            6, 20, commands.BucketType.user
        )
        self.consecutive_cooldowns: MutableMapping[int, int] = Counter()
        self.loop_task: Optional[asyncio.Task] = None

    async def bg_loop(self):
        # This is non-precise block age-outs
        while await asyncio.sleep(7200, True):
            self.prev_blocks = self.blocked
            self.blocked = discord.utils.SnowflakeList(())

    async def custom_before_invoke(self, ctx: commands.Context):

        if await ctx.bot.is_owner(ctx.author):
            return

        retry_time = self.cooldown.update_rate_limit(ctx.message)

        author_id = ctx.author.id

        if retry_time:
            self.consecutive_cooldowns[author_id] += 1
            if (ccc := self.consecutive_cooldowns[author_id]) > 3:
                if not self.blocked.has(author_id):
                    self.blocked.add(author_id)
                log.info(
                    "User: {user_id} has been blocked temporarily for "
                    "hitting the global ratelimit a lot.",
                    user_id=author_id,
                )

            message = self.messages[min(ccc, 4)]
            raise commands.UserFeedbackCheckFailure(message)

        else:

            self.consecutive_cooldowns.pop(author_id, None)

    async def custom_check_once(self, ctx: commands.Context):
        return not (
            self.blocked.has(ctx.author.id) or self.prev_blocks.has(ctx.author.id)
        )

    @classmethod
    async def setup(cls, bot: Red):
        c = cls(bot)
        bot.add_cog(c)
        bot.add_check(c.custom_check_once, call_once=True)
        bot.before_invoke(c.custom_before_invoke)
        c.loop_task = asyncio.create_task(c.bg_loop())

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.custom_before_invoke)
        self.bot.remove_check(self.custom_check_once, call_once=True)
        if self.loop_task:
            self.loop_task.cancel()

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

        message = " ".join(f"<@!{idx}>" for idx in (*self.blocked, *self.prev_blocks))

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
        self.prev_blocks = discord.utils.SnowflakeList(())
        await ctx.tick()

    @anticommandspam.command(name="remove")
    async def acs_remove(self, ctx: commands.Context, user_id: int):
        """ Remove a user id from the spam list """
        if self.blocked.has(user_id):
            self.blocked.remove(user_id)

        if self.prev_blocks.has(user_id):
            self.prev_blocks.remove(user_id)

        await ctx.tick()
