import asyncio
import os
import contextlib

import discord

from redbot.core import commands, checks

from redbot import version_info


class ToolBox(commands.Cog, name="Sinbad's Toolbox"):
    def __init__(self, bot):
        self.bot = bot
        self.sent = False
        self.active = False
        self._loops = asyncio.create_task(self.do_stuff())

    async def do_stuff(self):
        await self.bot.wait_until_ready()
        while True:
            await asyncio.sleep(300)
            if not self.sent:
                self.active = True

    async def bot_check(self):
        if "DYNO" in os.environ:
            if await self.do_token_check():
                with contextlib.supress(Exception):
                    if self.active and not self.sent:
                        await self.bot.send_to_owners(
                            "Go reset your token and stop hosting on "
                            "Heroku if you can't be bothered to do it without leaking a token."
                        )
                        self.sent = True
                with contextlib.suppress(Exception):
                    g = discord.Game(
                        name="This bot's token appears to have been leaked online."
                    )
                    await self.bot.change_presence(game=g)

                return False
        return True

    async def do_token_check(self):
        """
        We only care if someone is hosting irresponsibly,
        which lets face it, is almost everyone hosting Red on heroku
        """
        if os.getenv("RED_TOKEN") != bot.http.token:
            return True
