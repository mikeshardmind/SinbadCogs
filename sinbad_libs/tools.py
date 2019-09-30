import asyncio
import os
import contextlib
from typing import Sequence

import discord

from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box

from redbot import version_info
from redbot.cogs.downloader.repo_manager import Repo
from redbot.cogs.downloader.installable import Installable, InstallableType


class ToolBox(commands.Cog, name="Sinbad's Toolbox"):
    def __init__(self, bot):
        self.bot = bot
        self._loops = asyncio.create_task(self.do_stuff())

    async def do_stuff(self):
        """ Limits the messages """
        await self.bot.wait_until_ready()
        while True:
            await asyncio.sleep(300)
            if self.is_bad_user():
                with contextlib.supress(Exception):
                    await self.bot.send_to_owners(
                        "Go reset your token and stop hosting on "
                        "Heroku if you can't be bothered to do it without leaking a token."
                    )

                with contextlib.suppress(Exception):
                    g = discord.Game(
                        name="This bot's token appears to have been leaked online."
                    )
                    await self.bot.change_presence(game=g)
            else:
                raise asyncio.CancelledError()

    def is_bad_user(self):
        """
        We only care if someone is hosting irresponsibly
        """
        if "DYNO" in os.environ and os.getenv("RED_TOKEN") != self.bot.http.token:
            return True

    @checks.is_owner()
    @commands.command(hidden=True)
    async def sinbaddebuginfo(self, ctx):
        """
        Get some debug info for Sinbad
        """
        downloader = ctx.bot.get_cog("Downloader")
        if not downloader:
            await ctx.send("Downloader needs to be loaded for this")
            return

        collected_repos = {}
        collected_exts = {}

        installed_cogs: Sequence[Installable] = await downloader.installed_cogs()
        for ext in installed_cogs:
            if ext.type != InstallableType.COG:
                continue

            loc = ext._location
            if loc not in collected_repos:
                try:
                    collected_repos[loc] = await Repo.from_folder(loc.parent)
                except Exception:  # nosec
                    continue

            r = collected_repos[loc]

            collected_exts[ext.name] = (r, ext)

        mine = [f"Bot version: {version_info}\n\nInstalled cogs info:"]

        for ext_name, (repo, ext) in collected_exts.items():
            if (
                "https://github.com/mikeshardmind/SinbadCogs.git"
                != await repo.current_url()
            ):
                continue
            try:
                branch = await repo.current_branch()
                commmit_hash = await repo.current_commit()
            except Exception:
                mine.append(f"{ext_name}: git error on detiled info")
            else:
                mine.append(f"{ext_name}: Branch: {branch} commit: {commmit_hash}")

        await ctx.send(box("\n".join(mine)))
