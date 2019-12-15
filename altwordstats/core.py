from __future__ import annotations

import asyncio
import re
from math import log10
from typing import List

import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box

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
                );
                """
            )

    @staticmethod
    def sanitized_words_from_message(msg: discord.Message) -> List[str]:
        return sub_pattern.sub("", msg.content or "").split()

    @commands.Cog.listener("on_message_without_command")
    async def words_handler(self, message: discord.Message):

        if message.guild is None or message.bot:
            return

        gid = message.guild.id
        aid = message.author.id

        with self._connection.transaction() as cursor:
            for word in self.sanitized_words_from_message(message):
                cursor.execute(
                    """
                    INSERT INTO member_words(guild_id, author_id, word) VALUES (?,?,?)
                      ON CONFLICT(guild_id, author_id, word)
                        DO UPDATE SET quant = quant + 1;
                    """,
                    (gid, aid, word),
                )

    @commands.guild_only()
    @commands.group()
    async def wordstats(self, ctx: commands.Context):
        """ Stats about word usage """
        ...

    @wordstats.command()
    async def mytophere(self, ctx: commands.Context):
        """ Get your most used words in this guild """

        with self._connection.with_cursor() as cursor:
            results = cursor.execute(
                """
                SELECT quant, word FROM member_words
                WHERE guild_id = ? AND author_id = ?
                ORDER BY quant DESC
                LIMIT 20;
                """,
                (ctx.guild.id, ctx.author.id),
            ).fetchall()

        mx_width = log10(results[0][0]) // 1 + 1

        output = "\n".join(
            f"{i:>3}.   {count:>{mx_width}}   {word}"
            for i, (count, word) in enumerate(results, 1)
        )

        await ctx.send(box(output))

    @wordstats.command()
    async def mytop(self, ctx: commands.Context):
        """ Get your most used words (seen in any guild by this bot) """

        with self._connection.with_cursor() as cursor:
            results = cursor.execute(
                """
                SELECT SUM(quant) as wc, word
                FROM member_words WHERE author_id = ?
                GROUP BY word
                ORDER BY wc DESC
                LIMIT 20;
                """,
                (ctx.author.id,),
            ).fetchall()

        mx_width = log10(results[0][0]) // 1 + 1

        output = "\n".join(
            f"{i:>3}.   {count:>{mx_width}}   {word}"
            for i, (count, word) in enumerate(results, 1)
        )

        await ctx.send(box(output))

    @wordstats.command()
    async def servertop(self, ctx: commands.Context):
        """ Get the server's most used words """

        with self._connection.with_cursor() as cursor:
            results = cursor.execute(
                """
                SELECT SUM(quant) as wc, word
                FROM member_words WHERE guild_id = ?
                GROUP BY word
                ORDER BY wc DESC
                LIMIT 20;
                """,
                (ctx.guild.id,),
            ).fetchall()

        mx_width = log10(results[0][0]) // 1 + 1

        output = "\n".join(
            f"{i:>3}.   {count:>{mx_width}}   {word}"
            for i, (count, word) in enumerate(results, 1)
        )

        await ctx.send(box(output))
