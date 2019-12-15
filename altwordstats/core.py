from __future__ import annotations

import asyncio
import re
from math import log10
from typing import Callable, List, Optional

import apsw
import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box, pagify

from .apsw_wrapper import Connection

sub_pattern = re.compile(r"[^a-z\s]")


class WordStats(commands.Cog):
    """
    This is me playing with ideas prior to offering a PR.

    This won't be publicly exposed in the repo commands,
    but if you've found this, have fun
    """

    def __init__(self, bot: Red):
        self.bot = bot
        pth = cog_data_path(self) / "words.db"
        self._connection = Connection(pth)
        self._ready_event = asyncio.Event()
        self._init_task = asyncio.create_task(self.initialize())

    def cog_unload(self):
        self._ready_event.clear()
        self._init_task.cancel()

    async def initialize(self):
        with self._connection.with_cursor() as cursor:
            cursor.execute("""PRAGMA journal_mode=wal""")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS member_words(
                    guild_id INTEGER NOT NULL,
                    author_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    quant INTEGER DEFAULT 1,
                    PRIMARY KEY(guild_id, author_id, word)
                )
                """
            )

    @staticmethod
    def sanitized_words_from_message(msg: discord.Message) -> List[str]:
        return sub_pattern.sub("", msg.content or "").split()

    @commands.Cog.listener("on_message_without_command")
    async def words_handler(self, message: discord.Message):

        if message.guild is None or message.author.bot:
            return

        gid = message.guild.id
        aid = message.author.id

        with self._connection.transaction() as cursor:
            for word in self.sanitized_words_from_message(message):
                cursor.execute(
                    """
                    INSERT INTO member_words(guild_id, author_id, word) VALUES (?,?,?)
                      ON CONFLICT(guild_id, author_id, word) DO UPDATE SET quant=quant+1
                    """,
                    (gid, aid, word),
                )

    def query_results(
        self, query: str, *args, transformer: Optional[Callable] = None, **kwargs
    ) -> Optional[str]:

        with self._connection.with_cursor() as cursor:
            results = cursor.execute(query, args or kwargs).fetchall()

        if not results:
            return None

        num_col_width = int(log10(results[0][0])) + 4
        if transformer:
            results = map(transformer, results)
        output = "\n".join(f"{count:<{num_col_width}}{word}" for count, word in results)
        return output

    @staticmethod
    async def send_boxed(ctx: commands.Context, data: Optional[str] = None):
        if data:
            for page in pagify(data):
                await ctx.send(box(page))

    @commands.guild_only()
    @commands.group()
    async def wordstats(self, ctx: commands.Context):
        """ Stats about word usage """
        ...

    @wordstats.command()
    async def mytophere(self, ctx: commands.Context, limit: int = 10):
        """ Get your most used words in this guild """
        data = self.query_results(
            """
            SELECT quant, word FROM member_words
            WHERE guild_id = ? AND author_id = ?
            ORDER BY quant DESC
            LIMIT ?
            """,
            ctx.guild.id,
            ctx.author.id,
            limit,
        )
        await self.send_boxed(ctx, data)

    @wordstats.command()
    async def mytop(self, ctx: commands.Context, limit: int = 10):
        """ Get your most used words (seen in any guild by this bot) """

        data = self.query_results(
            """
            SELECT SUM(quant) as wc, word
            FROM member_words WHERE author_id = ?
            GROUP BY word
            ORDER BY wc DESC
            LIMIT ?
            """,
            ctx.author.id,
            limit,
        )
        await self.send_boxed(ctx, data)

    @checks.is_owner()
    @wordstats.command()
    async def topglobal(self, ctx: commands.Context, limit: int = 10):
        """ Anywhere """
        data = self.query_results(
            """
            SELECT SUM(quant) as wc, word
            FROM member_words
            GROUP BY word
            ORDER BY wc DESC
            LIMIT ?
            """,
            limit,
        )
        await self.send_boxed(ctx, data)

    @wordstats.command()
    async def servertop(self, ctx: commands.Context, limit: int = 10):
        """ Get the server's most used words """
        data = self.query_results(
            """
            SELECT SUM(quant) as wc, word
            FROM member_words WHERE guild_id = ?
            GROUP BY word
            ORDER BY wc DESC
            LIMIT ?
            """,
            ctx.guild.id,
            limit,
        )
        await self.send_boxed(ctx, data)

    @wordstats.command()
    async def wordtopserver(self, ctx: commands.Context, word: str, limit: int = 10):
        """ people who use a word the most """
        data = self.query_results(
            """
            SELECT quant, author_id FROM member_words
            WHERE guild_id = ? AND word = ?
            ORDER BY quant DESC
            LIMIT ?
            """,
            ctx.guild.id,
            word.lower(),
            limit,
            transformer=lambda args: (
                args[0],
                ctx.guild.get_member(args[1]) or "Unknown Member#0000",
            ),
        )
        await self.send_boxed(ctx, data)

    @checks.is_owner()
    @wordstats.command()
    async def wordtopglobal(self, ctx: commands.Context, word: str, limit: int = 10):
        """ people who use a word the most """
        data = self.query_results(
            """
            SELECT SUM(quant) as wc, author_id FROM member_words
            WHERE word = ?
            GROUP BY author_id
            ORDER BY wc DESC
            LIMIT ?
            """,
            word.lower(),
            limit,
            transformer=lambda args: (
                args[0],
                ctx.bot.get_user(args[1]) or "Unknown User#0000",
            ),
        )
        await self.send_boxed(ctx, data)

    @checks.is_owner()
    @wordstats.command()
    async def debug(self, ctx: commands.Context, *, query: str):
        """ query on data manually """

        try:
            with self._connection.with_cursor() as cursor:
                r = "\n".join(map(str, cursor.execute(query).fetchall()))
        except apsw.Error as exc:
            r = f"{type(exc)}{exc}"

        await ctx.send_interactive(pagify(r), box_lang="py")

    @wordstats.command()
    async def serveroverview(self, ctx: commands.Context):
        """ overviews """

        with self._connection.with_cursor() as cursor:
            results = cursor.execute(
                """
                SELECT
                  COUNT(DISTINCT word), SUM(quant), MAX(quant), AVG(quant)
                FROM member_words WHERE guild_id = ?
                """,
                (ctx.guild.id,),
            ).fetchone()

        if results:
            unique, total, most, avg = results
            await ctx.send(
                f"I have observed  a total of {total} words in this server. "
                f"Of those, there were {unique} unique words."
                f"\nAdditional info Max: {most} AVG: {avg}"
            )

    @checks.is_owner()
    @wordstats.command()
    async def globaloverview(self, ctx: commands.Context):
        """ overviews """

        with self._connection.with_cursor() as cursor:
            results = cursor.execute(
                """
                SELECT
                  COUNT(DISTINCT word), SUM(quant), MAX(quant), AVG(quant)
                FROM member_words
                """
            ).fetchone()

        if results:
            unique, total, most, avg = results
            await ctx.send(
                f"I have observed a total of {total} words. "
                f"Of those, there were {unique} unique words."
                f"\nAdditional info Max: {most} AVG: {avg}"
            )
