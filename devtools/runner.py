from __future__ import annotations

import asyncio
import contextlib
import functools
import io
import os
import subprocess  # nosec
import sys
from typing import List

import discord
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS


class Runner(commands.Cog):
    """
    Look, it works. Be careful when using this.
    """

    __version__ = "333.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self._futures: List[asyncio.Future] = []

    def cog_unload(self):
        for fut in self._futures:
            fut.cancel()

    def get_env(self) -> dict:
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
        return env

    async def run(self, ctx: commands.Context, command: str, to_file=False):

        env = self.get_env()

        async with ctx.typing():
            p = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )

            f = asyncio.create_task(p.communicate())

            def kill_if_cancelled(p: asyncio.subprocess.Process, f: asyncio.Future):
                if f.cancelled():
                    with contextlib.suppress(Exception):
                        p.kill()

            f.add_done_callback(functools.partial(kill_if_cancelled, p))

            raw_result, _err = await f

        if to_file:
            fp = io.BytesIO(raw_result)
            fp.seek(0)
            await ctx.send(files=[discord.File(fp, filename=f"{ctx.message.id}.log")])
        else:
            result = raw_result.decode()
            if not result:
                await ctx.tick()
            else:
                rpages = [
                    box(p) for p in pagify(result, shorten_by=(len(command) + 100))
                ]
                plen = len(rpages)
                pages = [
                    f"Page {index} / {plen} of output for\n{box(command)}\n{rpage}"
                    for index, rpage in enumerate(rpages, 1)
                ]
                await menu(ctx, pages, DEFAULT_CONTROLS)

    @checks.is_owner()
    @commands.command()
    async def shell(self, ctx: commands.Context, *, command: str):
        """
        Runs a command.
        """
        f = asyncio.create_task(self.run(ctx, command, to_file=True))
        self._futures.append(f)

    @checks.is_owner()
    @commands.command()
    async def shelld(self, ctx: commands.Context, *, command: str):
        """
        Runs a command, output in chat.
        """
        f = asyncio.create_task(self.run(ctx, command, to_file=False))
        self._futures.append(f)

    @checks.is_owner()
    @commands.command()
    async def killshells(self, ctx: commands.Context):
        """
        kills the shells
        """
        for f in self._futures:
            f.cancel()
        await ctx.tick()
