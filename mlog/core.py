from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import List, Literal, Optional, Set

import apsw
import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

from .apsw_wrapper import Connection


class MLog(commands.Cog):
    """ WIP """

    __end_user_data_statement__ = (
        "This cog logs messages and does not respect the data APIs. "
        "Bot owners have been warned against loading this cog as it is a work in progress. "
        "Bot owners will recieve notice of attempts to delete data and it is on them to handle "
        "this manually at the current time."
    )

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord", "owner", "user", "user_strict"],
        user_id: int,
    ):
        await self.bot.send_to_owners(
            f"Data deletion request for `MLog` by {requester} for user id {user_id}."
        )

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.active_guild_ids: Set[int] = set()
        fp = cog_data_path(self) / "data.db"
        self._connection = Connection(fp)
        self._ready_event = asyncio.Event()
        self._init_task: Optional[asyncio.Task] = None

    def init(self):
        self._init_task = asyncio.create_task(self.initialize())

    def cog_unload(self):
        if self._init_task is not None:
            self._init_task.cancel()
        self._ready_event.clear()
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
            cursor.execute("""PRAGMA foreign_keys = ON""")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages(
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    author_id INTEGER,
                    content TEXT,
                    created_at INTEGER
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS edits(
                    uid INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER REFERENCES messages(message_id)
                        ON UPDATE CASCADE ON DELETE CASCADE,
                    edited_at INTEGER NOT NULL,
                    new_content TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_settings(
                    guild_id INTEGER PRIMARY KEY,
                    active BOOLEAN DEFAULT false,
                    attachments BOOLEAN DEFAULT false,
                    bots BOOLEAN DEFAULT true,
                    last_build INTEGER DEFAULT 0
                )
                """
            )

        self._ready_event.set()

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        await self._ready_event.wait()
        message_id = payload.message_id
        data = payload.data

        try:
            new_content = data["content"]
        except KeyError:
            return

        with suppress(apsw.ConstraintError), self._connection.with_cursor() as cursor:

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
                INSERT OR IGNORE INTO messages(
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
    async def mhistory(self, ctx: commands.Context, message_id: int):
        """
        Get the history of a message.
        """
        with self._connection.with_cursor() as cursor:
            results = cursor.execute(
                """
                SELECT
                    messages.content,
                    messages.created_at,
                    edits.new_content,
                    edits.edited_at
                FROM edits
                INNER JOIN messages ON messages.message_id=edits.message_id
                WHERE messages.message_id = ?
                ORDER BY edits.edited_at
                """,
                (message_id,),
            ).fetchall()

        if not results:
            return await ctx.send("No edits recorded for this message")

        last_content = None
        embeds: List[discord.Embed] = []

        color = await ctx.embed_color()

        for original_con, original_dat, edit_con, edit_dat in results:
            if last_content is None:

                e = discord.Embed(
                    color=color, timestamp=datetime.fromtimestamp(original_dat)
                )
                e.add_field(name="Original Content", value=original_con)
                embeds.append(e)

                last_content = original_con

            e = discord.Embed(color=color, timestamp=datetime.fromtimestamp(edit_dat))
            e.add_field(name="Edited from", value=last_content, inline=False)
            e.add_field(name="Edited to", value=edit_con, inline=False)
            embeds.append(e)
            last_content = edit_con

        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @checks.is_owner()
    @commands.command()
    async def mldebug(self, ctx: commands.Context, *, query: str):
        """ Hmm """

        try:
            with self._connection.with_cursor() as cursor:
                r = "\n".join(map(str, cursor.execute(query).fetchall()))
        except apsw.Error as exc:
            r = f"{type(exc)}{exc}"

        await ctx.tick()
        await ctx.send_interactive(pagify(r), box_lang="py")

    @checks.is_owner()
    @commands.command()
    async def mlbuild(self, ctx: commands.Context, guild_id: int):
        """ go build message history """

        now = int(ctx.message.created_at.timestamp())

        guild = ctx.bot.get_guild(guild_id)
        if not guild:
            return await ctx.send("No such guild.")

        channels = [
            c
            for c in guild.text_channels
            if c.permissions_for(guild.me).read_message_history
        ]

        with self._connection.with_cursor() as cursor:
            (last_build,) = cursor.execute(
                """
                SELECT COALESCE(
                    (SELECT last_build FROM guild_settings WHERE guild_id = ?), 0
                )
                """,
                (guild_id,),
            ).fetchone()
            after = max(
                datetime.fromtimestamp(last_build), discord.utils.snowflake_time(0)
            )

        async with ctx.typing():
            for channel in channels:
                async for message in channel.history(limit=None, after=after):
                    await self.on_message(message)
                    await asyncio.sleep(0.02)

        with self._connection.with_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO guild_Settings(guild_id, last_build) VALUES (?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET last_build=excluded.last_build
                """,
                (guild_id, now),
            )
        await ctx.tick()
