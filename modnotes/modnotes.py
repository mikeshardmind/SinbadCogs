from __future__ import annotations

import asyncio
from typing import Iterator, NamedTuple
from datetime import datetime

import discord

from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils import menus
from .converters import MemberOrID
from .apsw_wrapper import Connection


class Note(NamedTuple):
    uid: int
    author_id: int
    subject_id: int
    guild_id: int
    note: str
    created_at: int

    def embed(self, ctx, color) -> discord.Embed:
        e = discord.Embed(
            description=self.note,
            timestamp=datetime.fromtimestamp(self.created_at),
            color=color,
        )
        author = ctx.guild.get_member(self.author_id)
        subject = ctx.guild.get_member(self.subject_id)
        a_str = (
            f"{author} ({self.author_id})"
            if author
            else f"Unknown Author ({self.author_id})"
        )
        s_str = (
            f"{subject} ({self.subject_id})"
            if subject
            else f"Unknown Subject ({self.subject_id})"
        )
        e.add_field(name="Note Author", value=a_str)
        e.add_field(name="Note Subject", value=s_str)
        return e


class ModNotes(commands.Cog):
    """ Store moderation notes """

    __version__ = "323.0.1"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red):
        self.bot: Red = bot
        fp = str(cog_data_path(self) / "notes.db")
        self._connection = Connection(fp)
        self._ready_event = asyncio.Event()
        self._init_task = asyncio.create_task(self.initialize())

    async def initialize(self):
        await self.bot.wait_until_ready()
        with self._connection.with_cursor() as cursor:
            cursor.execute("""PRAGMA journal_mode=wal""")

            # rename if exists NOTES -> member_notes
            cursor.execute("""PRAGMA table_info("NOTES")""")
            if cursor.fetchone():
                cursor.execute("""ALTER TABLE NOTES RENAME TO member_notes""")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS member_notes (
                    uid INTEGER PRIMARY KEY AUTOINCREMENT,
                    author_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    note TEXT,
                    created INTEGER NOT NULL
                )
                """
            )
            # If lookups feel slow,
            # Consider an index later on member_notes(subject_id, guild_id)
        self._ready_event.set()

    async def cog_before_invoke(self, ctx):
        await self._ready_event.wait()

    def cog_unload(self):
        self._connection.close()

    def insert(self, *, author_id: int, subject_id: int, guild_id: int, note: str):
        with self._connection.with_cursor() as cursor:
            now = int(datetime.utcnow().timestamp())
            cursor.execute(
                """
                INSERT INTO member_notes(author_id, subject_id, guild_id, note, created)
                VALUES(?,?,?,?,?)
                """,
                (author_id, subject_id, guild_id, note, now),
            )

    def find_by_author(self, author_id: int) -> Iterator[Note]:
        with self._connection.with_cursor() as cursor:
            for items in cursor.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM member_notes
                WHERE author_id=?
                ORDER BY created
                """,
                (author_id,),
            ):
                yield Note(*items)

    def find_by_author_in_guild(
        self, *, author_id: int, guild_id: int
    ) -> Iterator[Note]:
        with self._connection.with_cursor() as cursor:
            for items in cursor.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM member_notes
                WHERE author_id=? AND guild_id=?
                ORDER BY created
                """,
                (author_id, guild_id),
            ):
                yield Note(*items)

    def find_by_member(self, *, member_id: int, guild_id: int) -> Iterator[Note]:
        with self._connection.with_cursor() as cursor:
            for items in cursor.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM member_notes
                WHERE subject_id=? AND guild_id=?
                ORDER BY created
                """,
                (member_id, guild_id),
            ):
                yield Note(*items)

    def find_by_guild(self, guild_id: int) -> Iterator[Note]:
        with self._connection.with_cursor() as cursor:
            for items in cursor.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM member_notes
                WHERE guild_id=?
                ORDER BY created
                """,
                (guild_id,),
            ):
                yield Note(*items)

    def delete_by_uid(self, uid: int):
        with self._connection.with_cursor() as cursor:
            cursor.execute("DELETE FROM NOTES WHERE uid=?", (uid,))

    @checks.mod()
    @commands.guild_only()
    @commands.command()
    async def makemodnote(self, ctx, user: MemberOrID, *, note: str):
        """ Make a note about a user """

        self.insert(
            author_id=ctx.author.id,
            subject_id=user.id,
            note=note,
            guild_id=ctx.guild.id,
        )
        await ctx.tick()

    @checks.mod()
    @commands.guild_only()
    @commands.group()
    async def getmodnotes(self, ctx):
        """ Get notes """
        pass

    @getmodnotes.command()
    async def about(self, ctx, user: MemberOrID):
        """ Get notes about a user """
        color = await ctx.embed_color()
        notes = [
            n.embed(ctx, color)
            for n in self.find_by_member(member_id=user.id, guild_id=ctx.guild.id)
        ]
        if not notes:
            return await ctx.send("No mod notes about this user")
        mx = len(notes)
        for i, n in enumerate(notes, 1):
            n.title = f"Showing #{i} of {mx} found notes"

        await menus.menu(ctx, notes, menus.DEFAULT_CONTROLS)
