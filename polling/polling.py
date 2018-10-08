import asyncio
from typing import Any
import discord
from datetime import datetime as dt, timedelta as td

from redbot.core import commands, checks
from redbot.core.bot import Red

Base: Any = getattr(commands, "Cog", object)


class Polling(Base):
    """
    A Polling cog
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "1.0.3"

    @commands.command()
    async def votecount(
        self, ctx: commands.Context, channel: discord.TextChannel, msgid: int
    ):
        """
        Get's a vote count
        """

        m = await channel.get_message(msgid)
        if m is None:
            return await ctx.maybe_send_embed("No such message in that channel.")

        responses = {
            str(r): [x for x in await r.users().flatten() if not x.bot]
            for r in m.reactions
        }

        await self.send_dict(ctx, responses)

    @commands.command()
    async def advvotecount(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        msgid: int,
        allowmultivote: bool,
        min_days: int = 0,
        *emojis: str,
    ):
        """
        gets votes,

        allowmultivote: allow/forbid multivoting
        min_days: min days in server to vote (optional)
        emojis: list of emoji to consider as votes (optional)
        """

        m = await channel.get_message(msgid)
        if m is None:
            return await ctx.maybe_send_embed("No such message in that channel.")

        responses: dict = {}
        users: list = []
        multivoters: list = []

        for r in m.reactions:
            if emojis and str(r) not in emojis:
                continue
            responses[str(r)] = []
            async for u in r.users():
                if u.bot:
                    continue
                if u in users:
                    multivoters.append(u)
                else:
                    users.append(u)
                responses[str(r)].append(u)

        valid_votes: dict = {k: [] for k in responses.keys()}

        for k, v in responses.items():
            for user in v:
                if dt.utcnow() - td(days=min_days) > user.joined_at:
                    if not ((not allowmultivote) and user in multivoters):
                        valid_votes[k].append(user)

        await self.send_dict(ctx, valid_votes)

    async def send_dict(self, ctx, some_dict: dict):

        msg = "Vote results:"

        for k, v in sorted(some_dict.items(), key=lambda x: len(x[1]), reverse=True):
            msg += "\n{emoji} : {count} {plural}".format(
                emoji=k, count=len(v), plural=("vote" if len(v) == 1 else "votes")
            )

        await ctx.maybe_send_embed(msg)
