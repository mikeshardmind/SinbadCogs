import asyncio
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

import discord
from redbot.core import commands, checks


class Inactivity(commands.Cog):
    """
    Select and/or remove inactive users
    """

    async def handle_channel(
        self, chan: discord.TextChannel
    ) -> Tuple[Dict[int, int], Dict[int, datetime]]:

        counts: Dict[int, int] = defaultdict(int)
        recents: Dict[int, datetime] = defaultdict(lambda: datetime.utcfromtimestamp(0))

        if chan.permissions_for(chan.guild.me).read_message_history:
            async for message in chan.history(limit=None):
                aid = message.author.id
                counts[aid] += 1
                recents[aid] = max(recents[aid], message.created_at)
        return counts, recents

    async def getinfo(
        self, guild: discord.Guild
    ) -> Tuple[Dict[int, int], Dict[int, datetime]]:

        full_counts: Dict[int, int] = defaultdict(int)
        full_recents: Dict[int, datetime] = defaultdict(
            lambda: datetime.utcfromtimestamp(0)
        )

        vals = await asyncio.gather(
            *[self.handle_channel(c) for c in guild.text_channels]
        )

        for counts, most_recents in vals:
            for idx, count in counts.items():
                full_counts[idx] += count
            for idx, most_recent in most_recents.items():
                full_recents[idx] = max(full_recents[idx], most_recent)

        return full_counts, full_recents
