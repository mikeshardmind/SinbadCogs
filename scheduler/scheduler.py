#   Copyright 2017-present Michael Hall
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional

import discord
from redbot.core import checks, commands
from redbot.core.config import Config
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .checks import can_run_command
from .converters import NonNumeric, Schedule, TempMute
from .tasks import Task

"""
To anyone that comes to this later to improve it, the number one improvement
which can be made is to stop storing just a unix timestamp.

Store a naive time tuple(limited granularity to seconds) with timezone code instead.

The scheduling logic itself is solid, even if not the easiest to reason about.

The patching of discord.TextChannel and fake discord.Message objects is *messy* but works.
"""

SUSPICIOUS_COMMANDS = ("restart", "shutdown", "reload")


class Scheduler(commands.Cog):
    """
    A somewhat sane scheduler cog.

    This cog has a known issue with timezone transtions
    """

    __author__ = "mikeshardmind(Sinbad), DiscordLiz"
    __version__ = "2021.03"
    __external_api_version__ = 1
    __external_supported_api__ = ("api_schedule", "api_unschedule")

    async def api_schedule(
        self,
        calling_cog: commands.Cog,
        *,
        command: str,
        author: discord.Member,
        channel: discord.TextChannel,
        initial: datetime,
        recur: Optional[timedelta] = None,
    ) -> str:
        """
        Schedule a command safely from another cog

        .. warning::

            This method should not be used except by those who verify for a matching API version


        .. warning::

            This cog does not currently handle DST transitions but may in the future


        .. note::

            Users may unschedule things your cog schedules on their behalf. This is intentional.


        Parameters
        ----------
        calling_cog: commands.Cog
            The cog you are scheduling from
        command: str
            The command the user will run, as text, without a prefix and with any needed arguments.
            No attempt is made to verify the validity of the command or it's usage here.
        author: discord.Member
            The member this task will run as.
        channel: discord.TextChannel
            The channel to schedule the command in.
        initial: datetime
            When the first instance should happen. If this is a naive datetime, UTC will be assumed.
        recur: Optional[timedelta]
            If provided, how frequently this will run. This must be at least a minute if provided.

        Returns
        -------
        str
            A string which is needed to unschedule the task

        Raises
        ------
        TypeError
        ValueError
        """

        # explain: mypy assumes this is always true, but other CCs using this API may not be using mypy.
        if not (isinstance(author, discord.Member) and isinstance(channel, discord.TextChannel)):  # type: ignore
            raise TypeError(
                "Must provide guild specific discord.py models for both author and channel"
            )

        if recur is not None and recur.total_seconds() < 60:
            raise ValueError("Recuring events must be at least a minute apart.")

        uid = uuid.uuid4().hex

        t = Task(
            uid=uid,
            nicename=f"Task scheduled by another cog: {calling_cog.qualified_name} | {uid}",
            author=author,
            content=command,
            channel=channel,
            initial=initial,
            recur=recur,
            extern_cog=calling_cog.qualified_name,
        )

        async with self._iter_lock:
            async with self.config.channel(channel).tasks(acquire_lock=False) as tsks:
                tsks.update(t.to_config())
            self.tasks.append(t)

        return uid

    async def api_unschedule(self, calling_cog: commands.Cog, uid: str):
        """
        Unschedule a command which was scheduled through the API

        This method will fail silently on already unscheduled or otherwise
        removed tasks to make it easier to safely work with the fact that
        users may also unschedule things, and non recurring tasks may get
        removed automatically.

        .. warning::

            This method should not be used except by those who verify for a matching API version


        Paramaters
        ----------
        calling_cog: commands.Cog
            The cog you are scheduling from
        uid: str
            A string which is needed to unschedule the task
        """

        tasks = await self.fetch_task_by_attrs_exact(
            extern_cog=calling_cog.qualified_name, uid=uid
        )
        if tasks:
            await self._remove_tasks(*tasks)

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_channel(tasks={})  # Serialized Tasks go in here.
        self.log = logging.getLogger("red.sinbadcogs.scheduler")
        self.bg_loop_task: Optional[asyncio.Task] = None
        self.scheduled: Dict[
            str, asyncio.Task
        ] = {}  # Might change this to a list later.
        self.tasks: List[Task] = []
        self._iter_lock = asyncio.Lock()

    def init(self):
        self.bg_loop_task = asyncio.create_task(self.bg_loop())

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        for task in self.scheduled.values():
            task.cancel()

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        loaded_tasks = await self.fetch_task_by_attrs_exact(author=user_id)
        if loaded_tasks:
            await self._remove_tasks(*loaded_tasks)

        chan_dict = await self.config.all_channels()
        c = 0
        for channel_id, channel_data in chan_dict.items():
            c += 1
            if not c % 100:
                await asyncio.sleep(0)

            collected = []
            if chan_tasks := channel_data.get("tasks"):
                for task_id, task in chan_tasks.items():
                    c += 1
                    if not c % 100:
                        await asyncio.sleep(0)
                    if task.get("author", 0) == user_id:
                        collected.append(task_id)

            if collected:
                async with self._iter_lock:
                    async with self.config.channel_from_id(channel_id).tasks() as tsks:
                        for task_id in collected:
                            tsks.pop(task_id, None)

    async def _load_tasks(self):
        chan_dict = await self.config.all_channels()
        for channel_id, channel_data in chan_dict.items():
            channel = self.bot.get_channel(channel_id)
            if (
                not channel
                or not channel.permissions_for(channel.guild.me).read_messages
            ):
                continue
            tasks_dict = channel_data.get("tasks", {})
            for t in Task.bulk_from_config(bot=self.bot, **tasks_dict):
                self.tasks.append(t)

    async def _remove_tasks(self, *tasks: Task):
        async with self._iter_lock:
            for task in tasks:
                self.tasks.remove(task)
                await self.config.channel(task.channel).clear_raw("tasks", task.uid)

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        _guilds = [
            g for g in self.bot.guilds if g.large and not (g.chunked or g.unavailable)
        ]
        await self.bot.request_offline_members(*_guilds)

        async with self._iter_lock:
            await self._load_tasks()
        while True:
            sleep_for = await self.schedule_upcoming()
            await asyncio.sleep(sleep_for)

    async def delayed_wrap_and_invoke(self, task: Task, delay: float):
        await asyncio.sleep(delay)
        task.update_objects(self.bot)
        chan = task.channel
        if not chan.permissions_for(chan.guild.me).read_messages:
            return
        message = await task.get_message(self.bot)
        context = await self.bot.get_context(message)
        context.assume_yes = True
        if (
            context.invoked_with
            and context.command
            and context.command.qualified_name in SUSPICIOUS_COMMANDS
        ):
            self.log.warning(
                f"Handling scheduled {context.command.qualified_name} "
                "if you are using this to avoid an issue with another cog, "
                "go get the other cog fixed. This use won't be supported."
            )

        await self.bot.invoke(context)

        if context.valid:
            return  # only check alias/CC when we didn't have a "real" command

        # No longer interested in extending this,
        # ideally the whole ephemeral commands idea
        # lets this be removed completely
        for cog_name in ("CustomCommands", "Alias"):
            if cog := self.bot.get_cog(cog_name):
                for handler_name in ("on_message", "on_message_without_command"):
                    if msg_handler := getattr(cog, handler_name, None):
                        await msg_handler(message)
                        break

    async def schedule_upcoming(self) -> int:
        """
        Schedules some upcoming things as tasks.
        """

        async with self._iter_lock:
            to_pop = []
            for k, v in self.scheduled.items():
                if v.done():
                    to_pop.append(k)
                    try:
                        v.result()
                    except Exception:
                        self.log.exception("Dead task ", exc_info=True)

            for k in to_pop:
                self.scheduled.pop(k, None)

        to_remove: list = []

        for task in self.tasks:
            delay = task.next_call_delay
            if delay < 30 and task.uid not in self.scheduled:
                self.scheduled[task.uid] = asyncio.create_task(
                    self.delayed_wrap_and_invoke(task, delay)
                )
                if not task.recur:
                    to_remove.append(task)

        await self._remove_tasks(*to_remove)

        return 15

    async def fetch_task_by_attrs_exact(self, **kwargs) -> List[Task]:
        def pred(item):
            try:
                return kwargs and all(getattr(item, k) == v for k, v in kwargs.items())
            except AttributeError:
                return False

        async with self._iter_lock:
            return [t for t in self.tasks if pred(t)]

    async def fetch_task_by_attrs_lax(
        self, lax: Optional[dict] = None, strict: Optional[dict] = None
    ) -> List[Task]:
        def pred(item):
            try:
                if strict and not all(getattr(item, k) == v for k, v in strict.items()):
                    return False
            except AttributeError:
                return False
            if lax:
                return any(getattr(item, k, None) == v for k, v in lax.items())
            return True

        async with self._iter_lock:
            return [t for t in self.tasks if pred(t)]

    async def fetch_tasks_by_guild(self, guild: discord.Guild) -> List[Task]:

        async with self._iter_lock:
            return [t for t in self.tasks if t.channel in guild.text_channels]

    # Commands go here

    @commands.check(lambda ctx: not ctx.assume_yes)
    @checks.mod_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command(usage="<eventname> <command> <args>")
    async def schedule(
        self, ctx: commands.GuildContext, event_name: NonNumeric, *, schedule: Schedule
    ):
        """
        Schedule something

        Usage:
            [p]schedule eventname command args

        args:

            you must provide one of:

                --start-in interval
                --start-at time

            you may also provide:

                --every interval

            for recurring tasks

        intervals look like:

            5 minutes
            1 minute 30 seconds
            1 hour
            2 days
            30 days
            (etc)

        times look like:
            February 14 at 6pm EDT

        times default to UTC if no timezone provided.

        Example use:

            [p]schedule autosync bansync True --start-at 12AM --every 1 day

        Example use with other parsed commands:

        [p]schedule autosyndicate syndicatebans --sources 133049272517001216 --auto-destinations -- --start-at 12AM --every 1 hour

        This can also execute aliases.
        """

        command, start, recur = schedule.to_tuple()

        t = Task(
            uid=str(ctx.message.id),
            nicename=event_name.parsed,
            author=ctx.author,
            content=command,
            channel=ctx.channel,
            initial=start,
            recur=recur,
        )

        quiet: bool = schedule.quiet

        if await self.fetch_task_by_attrs_exact(
            author=ctx.author, channel=ctx.channel, nicename=event_name.parsed
        ):
            if not quiet:
                return await ctx.send("You already have an event by that name here.")

        async with self._iter_lock:
            async with self.config.channel(ctx.channel).tasks(
                acquire_lock=False
            ) as tsks:
                tsks.update(t.to_config())
            self.tasks.append(t)

        if quiet:
            return

        ret = (
            f"Task Scheduled. You can cancel this task with "
            f"`{ctx.clean_prefix}unschedule {ctx.message.id}` "
            f"or with `{ctx.clean_prefix}unschedule {event_name.parsed}`"
        )

        if recur and t.next_call_delay < 60:
            ret += (
                "\nWith the initial start being set so soon, "
                "you might have missed an initial use being scheduled by the loop. "
                "You may find the very first expected run of this was missed or otherwise seems late. "
                "Future runs will be on time."  # fractions of a second in terms of accuracy.
            )

        await ctx.send(ret)

    @commands.check(lambda ctx: not ctx.assume_yes)
    @commands.guild_only()
    @commands.command()
    async def unschedule(self, ctx: commands.GuildContext, info: str):
        """
        Unschedule something.
        """

        tasks = await self.fetch_task_by_attrs_lax(
            lax={"uid": info, "nicename": info},
            strict={"author": ctx.author, "channel": ctx.channel},
        )

        if not tasks:
            await ctx.send(
                f"Hmm, I couldn't find that task. (try `{ctx.clean_prefix}showscheduled`)"
            )

        elif len(tasks) > 1:
            self.log.warning(
                f"Mutiple tasks where should be unique. Task data: {tasks}"
            )
            await ctx.send(
                "There seems to have been breakage here. "
                "Cleaning up and logging incident."
            )
            return

        else:
            await self._remove_tasks(*tasks)
            await ctx.tick()

    @checks.bot_has_permissions(add_reactions=True, embed_links=True)
    @commands.guild_only()
    @commands.command()
    async def showscheduled(
        self, ctx: commands.GuildContext, all_channels: bool = False
    ):
        """
        Shows your scheduled tasks in this, or all channels.
        """

        if all_channels:
            tasks = await self.fetch_tasks_by_guild(ctx.guild)
            tasks = [t for t in tasks if t.author == ctx.author]
        else:
            tasks = await self.fetch_task_by_attrs_exact(
                author=ctx.author, channel=ctx.channel
            )

        if not tasks:
            return await ctx.send("No scheduled tasks")

        await self.task_menu(ctx, tasks)

    async def task_menu(
        self,
        ctx: commands.GuildContext,
        tasks: List[Task],
        message: Optional[discord.Message] = None,
    ):

        color = await ctx.embed_color()

        async def task_killer(
            cog: "Scheduler",
            page_mapping: dict,
            ctx: commands.GuildContext,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            to_cancel = page_mapping.pop(page)
            await cog._remove_tasks(to_cancel)
            if page_mapping:
                tasks = list(page_mapping.values())
                if ctx.channel.permissions_for(ctx.me).manage_messages:
                    with contextlib.suppress(discord.HTTPException):
                        await message.remove_reaction("\N{NO ENTRY SIGN}", ctx.author)
                await cog.task_menu(ctx, tasks, message)
            else:
                with contextlib.suppress(discord.NotFound):
                    await message.delete()

        count = len(tasks)
        embeds = [
            t.to_embed(index=i, page_count=count, color=color)
            for i, t in enumerate(tasks, 1)
        ]

        controls = DEFAULT_CONTROLS.copy()
        page_mapping = {i: t for i, t in enumerate(tasks)}
        actual_task_killer = functools.partial(task_killer, self, page_mapping)
        controls.update({"\N{NO ENTRY SIGN}": actual_task_killer})
        await menu(ctx, embeds, controls, message=message)

    @commands.check(lambda ctx: not ctx.assume_yes)
    @commands.command(name="remindme", usage="<what to be reminded of> <args>")
    async def reminder(self, ctx: commands.GuildContext, *, reminder: Schedule):
        """
        Schedule a reminder DM from the bot

        Usage:
            [p]remindme to do something [args]

        args:

            you must provide one of:

                --start-in interval
                --start-at time

            you may also provide:

                --every interval

            for recurring reminders

        intervals look like:

            5 minutes
            1 minute 30 seconds
            1 hour
            2 days
            30 days
            (etc)

        times look like:
            February 14 at 6pm EDT

        times default to UTC if no timezone provided.

        example usage:
            `[p]remindme get some fresh air --start-in 4 hours`
        """

        command, start, recur = reminder.to_tuple()

        t = Task(
            uid=str(ctx.message.id),
            nicename=f"reminder-{ctx.message.id}",
            author=ctx.author,
            content=f"schedhelpers selfwhisper {command}",
            channel=ctx.channel,
            initial=start,
            recur=recur,
        )

        async with self._iter_lock:
            async with self.config.channel(ctx.channel).tasks(
                acquire_lock=False
            ) as tsks:
                tsks.update(t.to_config())
            self.tasks.append(t)

        await ctx.tick()

    @commands.check(lambda ctx: ctx.message.__class__.__name__ == "SchedulerMessage")
    @commands.group(hidden=True, name="schedhelpers")
    async def helpers(self, ctx: commands.GuildContext):
        """
        Helper commands for scheduler use.
        """
        pass

    @helpers.command(name="say")
    async def say(self, ctx: commands.GuildContext, *, content: str):
        await ctx.send(content)

    @helpers.command(name="selfwhisper")
    async def swhisp(self, ctx: commands.GuildContext, *, content: str):
        with contextlib.suppress(discord.HTTPException):
            await ctx.author.send(content)

    @commands.check(lambda ctx: not ctx.assume_yes)
    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def scheduleradmin(self, ctx: commands.GuildContext):
        """
        Administrative commands for scheduler.
        """
        pass

    @checks.is_owner()
    @scheduleradmin.command()
    async def deleteallbyuser(self, ctx: commands.Context, user_id: int):
        """
        Destructive, use with care.
        """
        await self.red_delete_data_for_user(requester="owner", user_id=user_id)
        await ctx.tick()

    @checks.bot_has_permissions(add_reactions=True, embed_links=True)
    @scheduleradmin.command()
    async def viewall(self, ctx: commands.GuildContext):
        """
        View all scheduled events in a guild.
        """

        tasks = await self.fetch_tasks_by_guild(ctx.guild)

        if not tasks:
            return await ctx.send("No scheduled tasks")

        await self.task_menu(ctx, tasks)

    @commands.check(lambda ctx: not ctx.assume_yes)
    @scheduleradmin.command()
    async def kill(self, ctx: commands.GuildContext, *, task_id: str):
        """
        Kill another user's task. (id only)
        """

        tasks = await self.fetch_task_by_attrs_exact(uid=task_id)

        if not tasks:
            await ctx.send(
                f"Hmm, I couldn't find that task. (try `{ctx.clean_prefix}showscheduled`)"
            )

        elif len(tasks) > 1:
            self.log.warning(
                f"Mutiple tasks where should be unique. Task data: {tasks}"
            )
            return await ctx.send(
                "There seems to have been breakage here. Cleaning up and logging incident."
            )

        else:
            await self._remove_tasks(*tasks)
            await ctx.tick()

    @commands.check(lambda ctx: not ctx.assume_yes)
    @scheduleradmin.command()
    async def killchannel(self, ctx, channel: discord.TextChannel):
        """
        Kill all tasks scheduled in a specified channel.
        """

        tasks = await self.fetch_task_by_attrs_exact(channel=channel)

        if not tasks:
            return await ctx.send("No scheduled tasks in that channel.")

        await self._remove_tasks(*tasks)
        await ctx.tick()

    @commands.check(lambda ctx: not ctx.assume_yes)
    @commands.guild_only()
    @commands.group()
    async def tempmute(self, ctx):
        """
        A binding for mute + scheduled unmute.

        This exists only until it is added to core red.

        This relies on core commands for mute/unmute.
        This *may* show up in help for people who cannot use it.

        This does not support voice mutes, sorry.
        """
        pass

    @can_run_command("mute channel")
    @tempmute.command(usage="<user> [reason] [args]")
    async def channel(self, ctx, user: discord.Member, *, mute: TempMute):
        """
        A binding for mute + scheduled unmute.

        This exists only until it is added to core red.

        args can be
            --until time
        or
            --for interval

        intervals look like:

            5 minutes
            1 minute 30 seconds
            1 hour
            2 days
            30 days
            (etc)

        times look like:
            February 14 at 6pm EDT

        times default to UTC if no timezone provided.
        """

        reason, unmute_time = mute

        now = datetime.now(timezone.utc)

        mute_task = Task(
            uid=f"mute-{ctx.message.id}",
            nicename=f"mute-{ctx.message.id}",
            author=ctx.author,
            content=f"mute channel {user.id} {reason}",
            channel=ctx.channel,
            initial=now,
            recur=None,
        )

        unmute_task = Task(
            uid=f"unmute-{ctx.message.id}",
            nicename=f"unmute-{ctx.message.id}",
            author=ctx.author,
            content=f"unmute channel {user.id} Scheduler: Scheduled Unmute",
            channel=ctx.channel,
            initial=unmute_time,
            recur=None,
        )

        async with self._iter_lock:
            self.scheduled[mute_task.uid] = asyncio.create_task(
                self.delayed_wrap_and_invoke(mute_task, 0)
            )

            async with self.config.channel(ctx.channel).tasks(
                acquire_lock=False
            ) as tsks:
                tsks.update(unmute_task.to_config())
            self.tasks.append(unmute_task)

    @can_run_command("mute server")
    @tempmute.command(usage="<user> [reason] [args]", aliases=["guild"])
    async def server(self, ctx, user: discord.Member, *, mute: TempMute):
        """
        A binding for mute + scheduled unmute.

        This exists only until it is added to core red.

        args can be
            --until time
        or
            --for interval

        intervals look like:

            5 minutes
            1 minute 30 seconds
            1 hour
            2 days
            30 days
            (etc)

        times look like:
            February 14 at 6pm EDT

        times default to UTC if no timezone provided.
        """

        reason, unmute_time = mute

        now = datetime.now(timezone.utc)

        mute_task = Task(
            uid=f"mute-{ctx.message.id}",
            nicename=f"mute-{ctx.message.id}",
            author=ctx.author,
            content=f"mute server {user.id} {reason}",
            channel=ctx.channel,
            initial=now,
            recur=None,
        )

        unmute_task = Task(
            uid=f"unmute-{ctx.message.id}",
            nicename=f"unmute-{ctx.message.id}",
            author=ctx.author,
            content=f"unmute server {user.id} Scheduler: Scheduled Unmute",
            channel=ctx.channel,
            initial=unmute_time,
            recur=None,
        )

        async with self._iter_lock:
            self.scheduled[mute_task.uid] = asyncio.create_task(
                self.delayed_wrap_and_invoke(mute_task, 0)
            )

            async with self.config.channel(ctx.channel).tasks(
                acquire_lock=False
            ) as tsks:
                tsks.update(unmute_task.to_config())
            self.tasks.append(unmute_task)
