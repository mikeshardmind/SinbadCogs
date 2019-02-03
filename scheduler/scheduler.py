import asyncio
import discord
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, no_type_check
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from .message import SchedulerMessage
from .logs import get_logger
from .tasks import Task
from .converters import Schedule, non_numeric

_ = Translator("And I think it's gonna be a long long time...", __file__)


@cog_i18n(_)
class Scheduler(commands.Cog):
    """
    A somewhat sane scheduler cog
    """

    __version__ = "1.0.7"
    __author__ = "mikeshardmind(Sinbad)"
    __flavor_text__ = "UX improvements"

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

    def __unload(self):
        self.bg_loop_task.cancel()
        [task.cancel() for task in self.scheduled.values()]

    # This never should be needed,
    # but it doesn't hurt to add and could cover a weird edge case.
    __del__ = __unload

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
        async with self._iter_lock:
            await self._load_tasks()
        while self is self.bot.get_cog("Scheduler"):
            sleep_for = await self.schedule_upcoming()
            await asyncio.sleep(sleep_for)

    async def delayed_wrap_and_invoke(self, task: Task, delay: int):
        await asyncio.sleep(delay)
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
            if delay < 30:
                self.scheduled[task.uid] = asyncio.create_task(
                    self.delayed_wrap_and_invoke(task, delay)
                )
                if not task.recur:
                    to_remove.append(task)

        await self._remove_tasks(*to_remove)

        return 30

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
    @commands.command()
    @no_type_check
    async def schedule(self, ctx, event_name: non_numeric, *, schedule: Schedule):
        """
        Schedule something

        Usage:
            [p]schedule eventname command [args]

        args:

            you must provide at least one of:

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

        await ctx.send(
            f"Task Scheduled. You can cancel this task with "
            f"{ctx.clean_prefix}unschedule {ctx.message.id} "
            f"or with `{ctx.clean_prefix}unschedule {event_name}`"
        )

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
            return await ctx.send(
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
        # TODO: This + administrative management of scheduled commands.

        if all_channels:
            tasks = await self.fetch_tasks_by_guild(ctx.guild)
            tasks = [t for t in tasks if t.author == ctx.author]
        else:
            tasks = await self.fetch_task_by_attrs_exact(
                author=ctx.author, channel=ctx.channel
            )

        if not tasks:
            return await ctx.send("No scheduled tasks")

        color = await ctx.embed_color()

        count = len(tasks)
        embeds = [
            t.to_embed(index=i, page_count=count, color=color)
            for i, t in enumerate(tasks, 1)
        ]

        await menu(ctx, embeds, DEFAULT_CONTROLS)
