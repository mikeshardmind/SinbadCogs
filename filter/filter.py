from redbot.cogs.filter import Filter as _Filter
from collections import defaultdict
import discord
from typing import Union, Set

try:
    import re2
except ImportError:
    re2 = None

import re


class Filter(_Filter):

    def __init__(self, bot):
        super().__init__(bot)
        self._additional_pattern_cache = defaultdict(list)

    def register_pattern(
        self, *, guild: discord.Guild, channel: discord.TextChannel = None, pattern: str
    ):
        if not re2:
            return False
        try:
            compiled = re2.compile(pattern)
        except re.error:
            return False
        else:
            self._additional_pattern_cache[(guild, channel)].append(compiled)
            return True

    async def filter_hits(
        self, text: str, server_or_channel: Union[discord.Guild, discord.TextChannel]
    ) -> Set[str]:

        try:
            guild = server_or_channel.guild
            channel = server_or_channel
        except AttributeError:
            guild = server_or_channel
            channel = None

        try:
            pattern = self.pattern_cache[(guild, channel)]
        except KeyError:
            word_list = set(await self.settings.guild(guild).filter())
            if channel:
                word_list |= set(await self.settings.guild(channel).filter())

            if not word_list:
                return word_list

            pattern = re.compile("|".join(rf"\b{re.escape(w)}\b" for w in word_list), flags=re.I)

            self.pattern_cache[(guild, channel)] = pattern

        hits = set(pattern.findall(text))

        # modifications below
        additional_patterns = self._additional_pattern_cache[(guild, channel)]
        if channel is not None:
            additional_patterns.extend(self._additional_pattern_cache[(guild, None)])

        for pattern in additional_patterns:
            match = pattern.search(text)
            if match:
                hits.add(match.group(0))

        return hits
