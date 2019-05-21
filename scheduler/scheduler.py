import asyncio
import contextlib
import functools
import discord
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, List, no_type_check
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n

# you can change this when breaking later --Liz
from .menus import menu, DEFAULT_CONTROLS

from .message import SchedulerMessage
from .logs import get_logger
from .tasks import Task
from .converters import Schedule, non_numeric, TempMute
from .checks import can_run_command

_ = Translator("And I think it's gonna be a long long time...", __file__)


@cog_i18n(_)
class Scheduler(commands.Cog):
    """
    A somewhat sane scheduler cog
    """

    __version__ = "1.0.27"
    __author__ = "mikeshardmind(Sinbad), DiscordLiz"
    __flavor_text__ = "Unhidden remindme."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_channel(tasks={})  # Serialized Tasks go in here.
        self.log = get_logger("sinbadcogs.scheduler")
        self.bg_loop_task = bot.loop.create_task(self.bg_loop())
        self.scheduled = {}  # Might change this to a list later.
        self.tasks = []
        self._iter_lock = asyncio.Lock()
        self._original_cleanup_check = None

        cleanup = bot.get_cog("Cleanup")
        if cleanup:
            self.try_patch_cleanup(cleanup)

    def cog_unload(self):
        self.bg_loop_task.cancel()
        for task in self.scheduled.values():
            task.cancel()
        self.log.handlers = []
        if self._original_cleanup_check:
            cog = self.bot.get_cog("Cleanup")
            if cog:
                cog.check_100_plus = self._original_cleanup_check

    __unload = cog_unload

    # This never should be needed,
    # but it doesn't hurt to add and could cover a weird edge case.
    __del__ = cog_unload

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
        while self is self.bot.get_cog("Scheduler"):
            sleep_for = await self.schedule_upcoming()
            await asyncio.sleep(sleep_for)

    async def delayed_wrap_and_invoke(self, task: Task, delay: int):
        await asyncio.sleep(delay)
        task.update_objects(self.bot)
        chan = task.channel
        if not chan.permissions_for(chan.guild.me).read_messages:
            return
        message = await task.get_message(self.bot)
        context = await self.bot.get_context(message)
        await self.bot.invoke(context)
        for cog_name in ("CustomCommands", "Alias"):
            cog = self.bot.get_cog(cog_name)
            if cog:
                await cog.on_message(message)
        # TODO: allow registering additional cogs to process on_message for.

    async def schedule_upcoming(self) -> int:
        """
        Schedules some upcoming things as tasks. 
        
        """

        # TODO: improve handlng of next time return

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

    @property
    def task_class(self):
        """ API class Access """
        return Task

    async def submit_task(self, task: Task):
        """ externally safe API """
        async with self._iter_lock:
            self.tasks.append(task)

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
                if strict:
                    if not all(getattr(item, k) == v for k, v in strict.items()):
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

    @checks.mod_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.command(usage="<eventname> <command> <args>")
    @no_type_check
    async def schedule(self, ctx, event_name: non_numeric, *, schedule: Schedule):
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
        schedule: Tuple[str, datetime, Optional[timedelta]]

        command, start, recur = schedule

        t = Task(
            uid=ctx.message.id,
            nicename=event_name,
            author=ctx.author,
            content=command,
            channel=ctx.channel,
            initial=start,
            recur=recur,
        )

        if await self.fetch_task_by_attrs_exact(
            author=ctx.author, channel=ctx.channel, nicename=event_name
        ):
            return await ctx.send("You already have an event by that name here.")

        async with self._iter_lock:
            async with self.config.channel(ctx.channel).tasks() as tsks:
                tsks.update(t.to_config())
            self.tasks.append(t)

        ret = (
            f"Task Scheduled. You can cancel this task with "
            f"`{ctx.clean_prefix}unschedule {ctx.message.id}` "
            f"or with `{ctx.clean_prefix}unschedule {event_name}`"
        )

        if recur and t.next_call_delay < 60:
            ret += (
                "\nWith the intial start being set so soon, "
                "you might have missed an initial use being scheduled by the loop. "
                "you may find the very first expected run of this was missed or otherwise seems late. "
                "Future runs will be on time."  # fractions of a second in terms of accuracy.
            )

        await ctx.send(ret)

    @commands.guild_only()
    @commands.command()
    async def unschedule(self, ctx, info):
        """
        unschedule something.
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
            return await ctx.send(
                "There seems to have been breakage here. Cleaning up and logging incident."
            )

        else:
            await self._remove_tasks(*tasks)
            await ctx.tick()

    @commands.guild_only()
    @commands.command()
    async def showscheduled(self, ctx: commands.Context, all_channels: bool = False):
        """ shows your scheduled tasks in this, or all channels """

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

    async def task_menu(self, ctx, tasks, message: Optional[discord.Message] = None):

        color = await ctx.embed_color()

        async def task_killer(
            cog: "Scheduler",
            page_mapping: dict,
            ctx: commands.Context,
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
        await menu(ctx, embeds, controls)

    @commands.command(name="remindme", usage="<what to be reminded of> <args>")
    async def reminder(self, ctx, *, reminder: Schedule):
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

        command, start, recur = reminder

        t = Task(
            uid=ctx.message.id,
            nicename=f"reminder-{ctx.message.id}",
            author=ctx.author,
            content=f"schedhelpers selfwhisper {command}",
            channel=ctx.channel,
            initial=start,
            recur=recur,
        )

        async with self._iter_lock:
            async with self.config.channel(ctx.channel).tasks() as tsks:
                tsks.update(t.to_config())
            self.tasks.append(t)

        await ctx.tick()

    @commands.check(lambda ctx: ctx.message.__class__.__name__ == "SchedulerMessage")
    @commands.group(hidden=True, name="schedhelpers")
    async def helpers(self, ctx):
        """ helper commands for scheduler use """
        pass

    @helpers.command(name="say")
    async def say(self, ctx, *, content):
        await ctx.send(content)

    @helpers.command(name="selfwhisper")
    async def swhisp(self, ctx, *, content):
        with contextlib.suppress(discord.HTTPException):
            await ctx.author.send(content)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group()
    async def scheduleradmin(self, ctx):
        """ Administrative commands for scheduler """
        pass

    @scheduleradmin.command()
    async def viewall(self, ctx):
        """ view all scheduled events in a guild """

        tasks = await self.fetch_tasks_by_guild(ctx.guild)

        if not tasks:
            return await ctx.send("No scheduled tasks")

        await self.task_menu(ctx, tasks)

    @scheduleradmin.command()
    async def kill(self, ctx, *, task_id):
        """ kill another user's task (id only) """

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

    @scheduleradmin.command()
    async def killchannel(self, ctx, channel: discord.TextChannel):
        """ kill all in a channel """

        tasks = await self.fetch_task_by_attrs_exact(channel=channel)

        if not tasks:
            return await ctx.send("No scheduled tasks in that channel.")

        await self._remove_tasks(*tasks)
        await ctx.tick()

    @commands.guild_only()
    @commands.group()
    async def tempmute(self, ctx):
        """
        binding for mute + scheduled unmute 
        This exists only until it is added to core red

        relies on core commands for mute/unmute
        This *may* show up in help for people who cannot use it.

        This does not support voice mutes, sorry.
        """
        pass

    @can_run_command("mute channel")
    @tempmute.command(usage="<user> [reason] [args]")
    async def channel(self, ctx, user: discord.Member, *, mute: TempMute):
        """
        binding for mute + scheduled unmute 
        This exists only until it is added to core red

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

            async with self.config.channel(ctx.channel).tasks() as tsks:
                tsks.update(unmute_task.to_config())
            self.tasks.append(unmute_task)

    @can_run_command("mute server")
    @tempmute.command(usage="<user> [reason] [args]", aliases=["guild"])
    async def server(self, ctx, user: discord.Member, *, mute: TempMute):
        """
        binding for mute + scheduled unmute 
        This exists only until it is added to core red

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

            async with self.config.channel(ctx.channel).tasks() as tsks:
                tsks.update(unmute_task.to_config())
            self.tasks.append(unmute_task)

    @commands.Cog.listener("on_cog_add")
    async def on_cog_add(self, cog):

        if cog.__class__.__name__ != "Cleanup":
            return

        self.try_patch_cleanup(cog)

    def try_patch_cleanup(self, cog: commands.Cog):
        to_alter = getattr(cog, "check_100_plus", None)

        if to_alter is None:
            return

        def wrapper(func):
            async def injected_on_check_100_plus(ctx, number):
                if ctx.message.__class__.__name__ == "SchedulerMessage":
                    return True

                return await func(ctx, number)

            return injected_on_check_100_plus

        self._original_cleanup_check = to_alter
        cog.check_100_plus = wrapper(to_alter)
        self.log.info("Patched redbot's cleanup cog's check_100_plus`")
