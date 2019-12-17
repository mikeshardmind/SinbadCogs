from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Set

import apsw
import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import pagify

from .apsw_wrapper import Connection


class MLog(commands.Cog):
    """ WIP """

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.active_guild_ids: Set[int] = set()
        fp = cog_data_path(self) / "data.db"
        self._connection = Connection(fp)
        self._ready_event = asyncio.Event()
        self._init_task = asyncio.create_task(self.initialize())

    def cog_unload(self):
        self._init_task.cancel()
        self._ready_event.unset()
        self._connection.close()

    async def cog_before_invoke(self, ctx):
        await self._ready_event.wait()

    async def initialize(self):
        await self.bot.wait_until_ready()
        if self.bot.user.id not in (275047522026913793, 365420182522429440):
            await self.bot.send_to_owners(
                """"
                You really shouldn't load WIP cogs. This cog (mlog)
                would normally come with a lot of disclaimers.
                It won't be supported as-is, and I suggest you
                unload it and wait until it is ready for use.
                You've been warned. --Sinbad
                """
            )
        with self._connection.with_cursor() as cursor:
            cursor.execute("""PRAGMA journal_mode=wal""")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages(
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    author_id INTEGER,
                    content TEXT,
                    created_at INT,
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS edits(
                    message_id INTEGER NOT NULL,
                    edited_at INTEGER NOT NULL,
                    new_content TEXT
                    uid INTEGER AUTOINCREMENT,
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_settings(
                    guild_id INTEGER PRIMARY KEY,
                    active BOOLEAN DEFAULT false,
                    attachments BOOLEAN DEFAULT false,
                    bots BOOLEAN DEFAULT false
                )
                """
            )

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        await self._ready_event.wait()
        message_id = payload.message_id
        data = payload.data

        try:
            new_content = data["content"]
            guild_id = int(data["guild_id"])
        except KeyError:
            return

        with self._connection.with_cursor() as cursor:
            if not cursor.execute(
                """
                SELECT 1
                FROM guild_settings
                WHERE guild_id = ? AND active
                """,
                (guild_id,),
            ).fetchone():
                return

            cursor.execute(
                """
                INSERT INTO edits(message_id, edited_at, new_content)
                VALUES(:mid, :now, :new_content)
                """,
                {
                    "mid": message_id,
                    "now": int(datetime.utcnow().timestamp()),
                    "new_content": new_content,
                },
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self._ready_event.wait()

        if (not message.guild) or message.author.bot:
            return

        with self._connection.with_cursor() as cursor:
            if not cursor.execute(
                """
                SELECT 1
                FROM guild_settings
                WHERE guild_id = ? AND active
                """,
                (message.guild.id,),
            ).fetchone():
                return

            cursor.execute(
                """
                INSERT INTO messages(
                    message_id,
                    guild_id,
                    channel_id,
                    author_id,
                    content,
                    created_at
                )
                VALUES (:mid, :gid, :cid, :aid, :content, :created_at)
                """,
                {
                    "mid": message.id,
                    "gid": message.guild.id,
                    "cid": message.channel.id,
                    "aid": message.author.id,
                    "content": message.content or "",
                    "created_at": int(message.created_at.timestamp()),
                },
            )

    @checks.is_owner()
    @commands.command()
    async def mldebug(self, ctx: commands.Context, *, query: str):
        """ Hmm """

        try:
            with self._connection.with_cursor() as cursor:
                r = "\n".join(map(str, cursor.execute(query).fetchall()))
        except apsw.Error as exc:
            r = f"{type(exc)}{exc}"

        await ctx.send_interactive(pagify(r), box_lang="py")
