from __future__ import annotations

import asyncio
from typing import Iterator, NamedTuple
from datetime import datetime

import apsw
import discord

from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils import menus
from .converters import MemberOrID


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

    def __init__(self, bot: Red):
        self.bot: Red = bot
        fp = str(cog_data_path(self) / "notes.db")
        self._connection = apsw.Connection(fp)
        self._ready_event = asyncio.Event()
        self._init_task = asyncio.create_task(self.initialize())

    async def initialize(self):
        await self.bot.wait_until_ready()
        try:
            cur = self._connection.cursor()
            cur.execute("PRAGMA journal_mode=wal")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS NOTES (
                    uid INTEGER PRIMARY KEY AUTOINCREMENT,
                    author_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    note TEXT,
                    created INTEGER NOT NULL
                )
                """
            )
        finally:
            cur.close()
        self._ready_event.set()

    async def cog_before_invoke(self, ctx):
        await self._ready_event.wait()

    def cog_unload(self):
        self._connection.close()

    def insert(self, *, author_id: int, subject_id: int, guild_id: int, note: str):
        try:
            cur = self._connection.cursor()
            now = int(datetime.utcnow().timestamp())
            cur.execute(
                """
                INSERT INTO NOTES(author_id, subject_id, guild_id, note, created)
                VALUES(?,?,?,?,?)
                """,
                (author_id, subject_id, guild_id, note, now),
            )
        finally:
            cur.close()

    def find_by_author(self, author_id: int) -> Iterator[Note]:
        try:
            cur = self._connection.cursor()
            for items in cur.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM NOTES
                WHERE author_id=?
                ORDER BY created
                """,
                (author_id,),
            ):
                yield Note(*items)
        finally:
            cur.close()

    def find_by_author_in_guild(
        self, *, author_id: int, guild_id: int
    ) -> Iterator[Note]:
        try:
            cur = self._connection.cursor()
            for items in cur.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM NOTES
                WHERE author_id=? AND guild_id=?
                ORDER BY created
                """,
                (author_id, guild_id),
            ):
                yield Note(*items)
        finally:
            cur.close()

    def find_by_member(self, *, member_id: int, guild_id: int) -> Iterator[Note]:
        try:
            cur = self._connection.cursor()
            for items in cur.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM NOTES
                WHERE subject_id=? AND guild_id=?
                ORDER BY created
                """,
                (member_id, guild_id),
            ):
                yield Note(*items)
        finally:
            cur.close()

    def find_by_guild(self, guild_id: int) -> Iterator[Note]:
        try:
            cur = self._connection.cursor()
            for items in cur.execute(
                """
                SELECT uid, author_id, subject_id, guild_id, note, created
                FROM NOTES
                WHERE guild_id=?
                ORDER BY created
                """,
                (guild_id,),
            ):
                yield Note(*items)
        finally:
            cur.close()

    def delete_by_uid(self, uid: int):
        try:
            cur = self._connection.cursor()
            cur.execute("DELETE FROM NOTES WHERE uid=?", (uid,))
        finally:
            cur.close()

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
        mx = len(notes)
        for i, n in enumerate(notes, 1):
            n.title = f"Showing #{i} of {mx} found notes"

        await menus.menu(ctx, notes, menus.DEFAULT_CONTROLS)

