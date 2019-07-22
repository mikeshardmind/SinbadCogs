import asyncio
import os
import contextlib

import discord

from redbot.core import commands, checks

from redbot import version_info


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
                    if self.active and not self.sent:
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

    async def bot_check(self, ctx):
        if self.is_bad_user():
            return False
        return True

    def is_bad_user(self):
        """
        We only care if someone is hosting irresponsibly,
        which lets face it, is almost everyone hosting Red on heroku
        """
        if "DYNO" in os.environ and os.getenv("RED_TOKEN") != self.bot.http.token:
            return True
