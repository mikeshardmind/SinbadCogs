from __future__ import annotations

import functools
import io
import os
import subprocess  # nosec
import sys
import threading
import queue
import weakref
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.thread import _worker  # type: ignore
from typing import Callable


import discord
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS


class NoAtExitExecutor(ThreadPoolExecutor):

    _idle_semaphore: threading.Semaphore
    _threads: set
    _work_queue: queue.SimpleQueue
    _thread_name_prefix: str
    _max_workers: int
    _initializer: Callable
    _initargs: tuple

    def _adjust_thread_count(self):
        """
        https://github.com/python/cpython/blob/3.8/Lib/concurrent/futures/thread.py
        minus 1 line, as we actually *don't* want CPython joining these at exit.
        """

        # if idle threads are available, don't spin new threads
        if self._idle_semaphore.acquire(timeout=0):
            return

        # When the executor gets lost, the weakref callback will wake up
        # the worker threads.
        def weakref_cb(_, q=self._work_queue):
            q.put(None)

        num_threads = len(self._threads)
        if num_threads < self._max_workers:
            thread_name = "%s_%d" % (self._thread_name_prefix or self, num_threads)
            t = threading.Thread(
                name=thread_name,
                target=_worker,
                args=(
                    weakref.ref(self, weakref_cb),
                    self._work_queue,
                    self._initializer,
                    self._initargs,
                ),
            )
            t.daemon = True
            t.start()
            self._threads.add(t)


class Runner(commands.Cog):
    """
    Look, it works. Be careful when using this.

    This cog is no longer supported.
    Details as to why are available at source.
    As of time of marked unsupported,
    the cog was functional and not expected to be fragile to changes.
    """

    __version__ = "323.0.4"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.executor = NoAtExitExecutor()

    def cog_unload(self):
        self.executor.shutdown(wait=False)

    async def _run(self, command):
        env = os.environ.copy()
        if hasattr(sys, "real_prefix") or sys.base_prefix != sys.prefix:
            # os.path.sep - this is folder separator, i.e. `\` on win or `/` on unix
            # os.pathsep - this is paths separator in PATH, i.e. `;` on win or `:` on unix
            # a wonderful idea to call them almost the same >.<
            if sys.platform == "win32":
                binfolder = f"{sys.prefix}{os.path.sep}Scripts"
                env["PATH"] = f"{binfolder}{os.pathsep}{env['PATH']}"
            else:
                binfolder = f"{sys.prefix}{os.path.sep}bin"
                env["PATH"] = f"{binfolder}{os.pathsep}{env['PATH']}"
        return (
            await self.bot.loop.run_in_executor(
                self.executor,
                functools.partial(
                    subprocess.run,
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,  # nosec
                    env=env,
                ),
            )
        ).stdout

    @checks.is_owner()
    @commands.command()
    async def shell(self, ctx: commands.Context, *, command: str):
        """
        Runs a command.
        """
        async with ctx.typing():
            result = await self._run(command)
            fp = io.BytesIO(result)
            fp.seek(0)
        await ctx.send(files=[discord.File(fp, filename=f"{ctx.message.id}.log")])

    @checks.is_owner()
    @commands.command()
    async def shelld(self, ctx: commands.Context, *, command: str):
        """
        Runs a command, output in chat.
        """
        async with ctx.typing():
            result = (await self._run(command)).decode()

        if not result:
            return await ctx.tick()

        rpages = [box(p) for p in pagify(result, shorten_by=(len(command) + 100))]
        plen = len(rpages)
        pages = [
            f"Page {index} / {plen} of output for\n{box(command)}\n{rpage}"
            for index, rpage in enumerate(rpages, 1)
        ]
        await menu(ctx, pages, DEFAULT_CONTROLS)

    @checks.is_owner()
    @commands.command()
    async def killshells(self, ctx: commands.Context):
        """
        kills the shells
        """
        await ctx.send(
            "So, the boundary between sync and async code sucks and this is broken right now. "
            "Restarting your bot will handle it."
        )
        return
        # self.executor.shutdown(wait=False)
        # self.executor = NoAtExitExecutor()
        # await ctx.tick()
