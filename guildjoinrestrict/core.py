from __future__ import annotations

import asyncio
import enum
import logging
import time
from datetime import datetime, timezone
from typing import List, Literal, NamedTuple, Optional

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path


class AddOnceHandler(logging.FileHandler):
    """
    Red's hot reload logic will break my logging if I don't do this.
    """


log = logging.getLogger("red.sinbadcogs.guildjoinrestrcit")
log.setLevel(logging.INFO)

for handler in log.handlers:
    # Red hotreload shit.... can't use isinstance, need to check not already added.
    if handler.__class__.__name__ == "AddOnceHandler":
        break
else:
    fp = cog_data_path(raw_name="GuildJoinRestrict") / "events.log"
    handler = AddOnceHandler(fp)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="%",
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)


@enum.unique
class CogBehaviorEnum(enum.IntFlag):
    NOOP = 0
    LEAVE = 1
    USE_BLOCK_MODE = 2
    USE_ALLOW_MODE = 4
    LOG_FILE = 8
    LOG_DISCORD = 16


class EventQueueItem(NamedTuple):
    where: int
    settings_used: CogBehaviorEnum
    when: datetime

    def __str__(self):
        when_s = self.when.strftime("%Y-%m-%d %H:%M:%S")
        m = [f"[{when_s}] Server ID: {self.where} | "]
        if CogBehaviorEnum.USE_BLOCK_MODE in self.settings_used:
            m.append("Marked as blocked | ")
        elif CogBehaviorEnum.USE_ALLOW_MODE in self.settings_used:
            m.append("Not marked as allowed | ")

        if CogBehaviorEnum.LEAVE in self.settings_used:
            m.append("Left server")
        else:
            m.append("No action beyond logging taken.")

        return "".join(m)


class GuildJoinRestrict(commands.Cog):
    """
    A cog to restrict which guilds [botname] can join.
    """

    __end_user_data_statement__ = (
        "This cog persistently stores the minimum "
        "amount of data needed to restrict guild joins to those allowed by settings. "
        "It will not respect data deletion by end users, nor can end users request "
        "their data from this cog since it only stores "
        "discord IDs and whether those IDs are allowed or denied. "
        "Discord IDs may occasionally be logged to a file as needed for audit purposes."
    )

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester == "discord":
            # user is deleted, just comply
            await self.config.user(user_id).clear()
        elif requester == "owner":
            await self.bot.send_to_owners(
                "`GuildJoinRestrict` recieved a data deletion request "
                f"from a bot owner for ID : `{user_id}`."
                "\nThis cog will remove the ID if you use the commands provided "
                "to remove settings for them, but is retaining the "
                "ID for operational purposes if you do not."
            )

    def __init__(self, bot):
        self.bot: Red = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True,
        )
        self.config.register_global(behavior=8, log_channel=None)
        self.config.register_guild(allowed=False, blocked=False)
        self.config.register_user(allowed=False, blocked=False)
        # asyncio.Queue isn't actually generic at runtime.
        self.event_queue = asyncio.Queue()  # type: asyncio.Queue[EventQueueItem]
        self._bg_loop_task: Optional[asyncio.Task] = None
        self._behavior = CogBehaviorEnum.NOOP
        self._channel_id: Optional[int] = None
        self._loaded = asyncio.Event()

    def cog_unload(self):
        self._loaded.clear()

        def error_callback(f: asyncio.Future):
            try:
                f.exception()
            except Exception as exc:
                log.exception("Queue flushing task died: ", exc_info=exc)

        t = asyncio.create_task(self._flush_on_unload())
        t.add_done_callback(error_callback)

    async def _flush_on_unload(self):

        remaining_events: List[EventQueueItem] = []

        while not self.event_queue.empty():
            try:
                ev = self.event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            remaining_events.append(ev)

        remaining_events.sort(key=lambda e: e.when)

        if CogBehaviorEnum.LOG_DISCORD not in self._behavior:
            for ev in remaining_events:
                self.event_queue.task_done()
            return

        log_channel = (
            self.bot.get_channel(self._channel_id) if self._channel_id else None
        )
        if not log_channel:
            return

        assert isinstance(log_channel, discord.TextChannel), "mypy"  # nosec

        if not log_channel.permissions_for(log_channel.guild.me).send_messages:
            return

        for chunk in (
            remaining_events[p : p + 10] for p in range(0, len(remaining_events), 10)
        ):
            to_send = "```\n" + ("\n".join(map(str, chunk))) + "\n```"

            try:
                await log_channel.send(to_send)
            except discord.HTTPException as exc:
                log.exception("Failed to send log to discord", exc_info=exc)
            for ev in chunk:
                self.event_queue.task_done()

    async def cog_before_invoke(self, ctx):
        await self._loaded.wait()

    async def load(self):
        await self.bot.wait_until_red_ready()
        behavior = await self.config.behavior()
        self._behavior = CogBehaviorEnum(behavior)
        self._channel_id = await self.config.log_channel()
        self._loaded.set()

    def init(self):
        self._bg_loop_task = asyncio.create_task(self._bg_loop_func())
        t = asyncio.create_task(self.load())

        def done_callback(fut: asyncio.Future):

            try:
                fut.exception()
            except asyncio.CancelledError:
                log.info("Didn't set up and was cancelled")
            except asyncio.InvalidStateError as exc:
                log.exception(
                    "We somehow have a done callback when not done?", exc_info=exc
                )
            except Exception as exc:
                log.exception("Unexpected exception during cog setup: ", exc_info=exc)

        t.add_done_callback(done_callback)

        def bg_loop_error_callback(fut: asyncio.Future):

            try:
                fut.exception()
            except asyncio.CancelledError:
                log.info("Background loop closed.")
            except Exception as exc:
                log.exception("Unhandled exception in background loop: ", exc_info=exc)

        self._bg_loop_task.add_done_callback(bg_loop_error_callback)

    async def _bg_loop_func(self):
        """
        This is to ensure that we don't spam a discord channel,
        grouping events by 10 distinct events or 2 minute interval,
        whichever occurs first
        """
        events: List[EventQueueItem]
        await self._loaded.wait()

        while True:
            try:
                events = []
                iter_start = time.monotonic()

                while (max_wait := (time.monotonic() - iter_start)) < 120:
                    try:
                        n = await asyncio.wait_for(self.event_queue.get(), max_wait)
                    except asyncio.TimeoutError:
                        continue
                    else:
                        events.append(n)
                    if len(events) >= 10:
                        break

                if not events:
                    continue

                events.sort(key=lambda e: e.when)

                log_channel = (
                    self.bot.get_channel(self._channel_id) if self._channel_id else None
                )
                if log_channel:
                    assert isinstance(log_channel, discord.TextChannel), "mypy"  # nosec

                    if (
                        log_channel
                        and log_channel.permissions_for(
                            log_channel.guild.me
                        ).send_messages
                        and CogBehaviorEnum.LOG_DISCORD in self._behavior
                    ):
                        to_send = "```\n" + ("\n".join(map(str, events))) + "\n```"

                        try:
                            await log_channel.send(to_send)
                        except discord.HTTPException as exc:
                            log.exception("Failed to send log to discord", exc_info=exc)
                        finally:
                            # This may result in an exceedingly rare double post
                            # but can only happen around cog unload with near
                            # perfect timing. The alternative preventing that
                            # can cause not posting these at all.
                            for event in events:
                                self.event_queue.task_done()
                            continue  # noqa: F703  # restriction lifted in 3.8

                for event in events:
                    self.event_queue.task_done()

            except asyncio.CancelledError:
                # need to be mindful of events not being in a bad state
                # at any point where a cancellation could occur
                for event in events:
                    # reinsert the item into the queue for flush
                    self.event_queue.task_done()
                    self.event_queue.put_nowait(event)
                raise

    # commands start here

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):

        await self._loaded.wait()
        needs_action = False

        behavior = self._behavior

        if CogBehaviorEnum.USE_BLOCK_MODE in behavior:

            if (await self.config.guild(guild).blocked()) or (
                await self.config.user(guild.owner).blocked()
            ):
                needs_action = True
        elif CogBehaviorEnum.USE_ALLOW_MODE in behavior:

            if not (
                (await self.config.guild(guild).allowed())
                or (await self.config.user(guild.owner).allowed())
            ):
                needs_action = True

        if not needs_action:
            return

        if CogBehaviorEnum.LOG_FILE in behavior:
            log.info(
                "Guild (%d) %s was joined without meeting settings",
                guild.id,
                guild.name,
            )
        if CogBehaviorEnum.LOG_DISCORD in behavior:
            self.event_queue.put_nowait(
                EventQueueItem(guild.id, behavior, datetime.now(timezone.utc))
            )
        if CogBehaviorEnum.LEAVE in behavior:
            if not await self.bot.is_owner(guild.owner):
                if CogBehaviorEnum.LOG_FILE in behavior:
                    log.info(
                        "Guild (%d) %s triggered guild leave", guild.id, guild.name
                    )
                await guild.leave()  # safety hatch for this.
            elif CogBehaviorEnum.LOG_FILE in behavior:
                log.info(
                    "Guild (%d) %s would have triggered guild leave, "
                    "but the guild owenr is also a bot owner",
                    guild.id,
                    guild.name,
                )

    @checks.is_owner()
    @commands.group(name="joinrestrictset")
    async def command_group(self, ctx: commands.Context):
        """
        Settings for how [botname] should handle joining new servers.
        """

    @command_group.command(name="mode")
    async def mode_command(self, ctx: commands.Context, mode: str):
        """
        Sets the mode in which the cog operates.

        This may be one of the following:
            "allowlist" for only allowing those explicitly specified
            "blocklist" for allowing with the exception of those specified
            "none" to not check settings at all.
        """

        if (m := mode.casefold()) not in ("allowlist", "blocklist", "none"):
            raise commands.BadArgument(
                "mode must be one of `allowlist`, `blocklist`, or `none`"
            )

        lock = self.config.behavior.get_lock()
        async with lock:
            behavior = self._behavior
            if m == "allowlist":
                behavior |= CogBehaviorEnum.USE_ALLOW_MODE
                behavior &= ~CogBehaviorEnum.USE_BLOCK_MODE
            elif m == "blocklist":
                behavior |= CogBehaviorEnum.USE_BLOCK_MODE
                behavior &= ~CogBehaviorEnum.USE_ALLOW_MODE
            else:
                behavior &= ~(
                    CogBehaviorEnum.USE_ALLOW_MODE | CogBehaviorEnum.USE_BLOCK_MODE
                )
            self._behavior = behavior
            await self.config.behavior.set(self._behavior.value)
        await ctx.tick()

    @command_group.command(name="logchannel")
    async def set_log_channel(self, ctx: commands.Context, channel_id: int):
        """
        Set the channel events will be logged to if logging to channel is enabled.
        """
        if channel := self.bot.get_channel(channel_id):
            assert channel is not None, "mypy"  # nosec
            lock = self.config.log_channel.get_lock()
            async with lock:
                self._channel_id = channel_id
                await self.config.log_channel.set(channel_id)
            await ctx.send(f"Log channel set to <#{channel_id}>")
        else:
            await ctx.send("I couldn't find that channel by specified id")

    @command_group.command(name="enablechannellogging")
    async def enable_channel_logging(self, ctx: commands.Context):
        """ enable channel logging """
        if CogBehaviorEnum.LOG_DISCORD in self._behavior:
            if not self._channel_id:
                return await ctx.send(
                    "Channel logging is already enabled, "
                    "but I don't have a channel set to log to yet."
                )

            if channel := self.bot.get_channel(self._channel_id):
                assert channel is not None, "mypy"  # nosec
                return await ctx.send(
                    f"Channel logging is already enabled on <#{channel.id}>"
                )
            else:
                return await ctx.send(
                    f"Channel logging is already enabled for channel with id "
                    f"`{self._channel_id}` however I can't find that channel.`"
                )

        else:

            lock = self.config.behavior.get_lock()
            async with lock:
                self._behavior |= CogBehaviorEnum.LOG_DISCORD
                await self.config.behavior.set(self._behavior.value)

            if not self._channel_id:
                return await ctx.send(
                    "Channel logging is enabled, "
                    "but I don't have a channel set to log to yet."
                )

            if channel := self.bot.get_channel(self._channel_id):
                assert channel is not None, "mypy"  # nosec
                return await ctx.send(f"Channel logging is enabled on <#{channel.id}>")
            else:
                return await ctx.send(
                    f"Channel logging is enabled for channel with id "
                    f"`{self._channel_id}` however I can't find that channel.`"
                )

    @command_group.command(name="disablechannellogging")
    async def disable_channel_logging(self, ctx: commands.Context):
        """ disables channel logging """

        if CogBehaviorEnum.LOG_DISCORD not in self._behavior:
            await ctx.send("Channel logging was already disabled.")
        else:
            lock = self.config.behavior.get_lock()
            async with lock:
                self._behavior &= ~CogBehaviorEnum.LOG_DISCORD
                await self.config.behavior.set(self._behavior.value)
            await ctx.send("Channel logging is now disabled.")

    @command_group.command(name="enableautomaticleave")
    async def enable_leave(self, ctx: commands.Context):
        """ Enables automatic leaving """

        if CogBehaviorEnum.LEAVE in self._behavior:
            await ctx.send("Automatic leaving is already enabled.")
        else:
            lock = self.config.behavior.get_lock()
            async with lock:
                self._behavior |= CogBehaviorEnum.LEAVE
                await self.config.behavior.set(self._behavior.value)
            await ctx.send("Automatic leaving is now enabled.")

    @command_group.command(name="disableautomaticleave")
    async def disable_leave(self, ctx: commands.Context):
        """ Disables automatic leaving. """

        if CogBehaviorEnum.LEAVE not in self._behavior:
            await ctx.send("Automatic leaving was already disabled.")
        else:
            lock = self.config.behavior.get_lock()
            async with lock:
                self._behavior &= ~CogBehaviorEnum.LEAVE
                await self.config.behavior.set(self._behavior.value)
            await ctx.send("Automatic leaving is now disabled.")

    @command_group.group(name="manageblocks")
    async def block_group_command(self, ctx: commands.Context):
        """ Commands for managing the blocked guilds and guild owners """

    @block_group_command.command(name="addguildid")
    async def add_guild_block(self, ctx: commands.Context, guild_id: int):
        """
        Add a guild id
        """
        await self.config.guild_from_id(guild_id).blocked.set(True)
        await ctx.tick()

    @block_group_command.command(name="addownerid")
    async def add_guild_owner_block(self, ctx: commands.Context, user_id: int):
        """
        Add a guild owner's id
        """
        await self.config.user_from_id(user_id).blocked.set(True)
        await ctx.tick()

    @block_group_command.command(name="removeguildid")
    async def remove_guild_block(self, ctx: commands.Context, guild_id: int):
        """
        Remove a guild id
        """
        await self.config.guild_from_id(guild_id).blocked.clear()
        await ctx.tick()

    @block_group_command.command(name="removeownerid")
    async def remove_guild_owner_block(self, ctx: commands.Context, user_id: int):
        """
        Remove a guild owner's id
        """
        await self.config.user_from_id(user_id).blocked.clear()
        await ctx.tick()

    @command_group.group(name="manageallows")
    async def allow_group_command(self, ctx: commands.Context):
        """ Commands for managing the allowed guilds and guild owners """

    @allow_group_command.command(name="addguildid")
    async def add_guild_allow(self, ctx: commands.Context, guild_id: int):
        """
        Add a guild id
        """
        await self.config.guild_from_id(guild_id).allowed.set(True)
        await ctx.tick()

    @allow_group_command.command(name="addownerid")
    async def add_guild_owner_allow(self, ctx: commands.Context, user_id: int):
        """
        Add a guild owner's id
        """
        await self.config.user_from_id(user_id).allowed.set(True)
        await ctx.tick()

    @allow_group_command.command(name="removeguildid")
    async def remove_guild_allow(self, ctx: commands.Context, guild_id: int):
        """
        Remove a guild id
        """
        await self.config.guild_from_id(guild_id).allowed.clear()
        await ctx.tick()

    @allow_group_command.command(name="removeownerid")
    async def remove_guild_owner_allow(self, ctx: commands.Context, user_id: int):
        """
        Remove a guild owner's id
        """
        await self.config.user_from_id(user_id).allowed.clear()
        await ctx.tick()
