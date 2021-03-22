#   Copyright 2017-present Michael Hall
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from __future__ import annotations

from typing import List, Optional, cast

import discord
from redbot.core.bot import Red


class NwayRelay:
    def __init__(self, *, bot: Red, channels: List[int]) -> None:
        self.channel_ids: List[int] = channels
        self.bot = bot

    @property
    def channels(self) -> List[discord.TextChannel]:
        ret: List[discord.TextChannel] = []
        for idx in self.channel_ids:
            c = self.bot.get_channel(idx)
            if c:
                assert isinstance(c, discord.TextChannel)  # nosec
                ret.append(c)
        return ret

    def get_destinations(self, message: discord.Message) -> List[discord.TextChannel]:
        if message.channel.id not in self.channel_ids:
            return []
        ret: List[discord.TextChannel] = []
        for idx in self.channel_ids:
            if idx == message.channel.id:
                continue
            c = self.bot.get_channel(idx)
            if c:
                assert isinstance(c, discord.TextChannel)  # nosec
                ret.append(c)
        return ret

    def to_data(self):
        return {"channels": self.channel_ids}


class OnewayRelay:
    def __init__(self, *, bot: Red, source: int, destinations: List[int]) -> None:
        self.source_id: int = source
        self.destination_ids: List[int] = destinations
        self.bot: Red = bot

    @property
    def source(self) -> Optional[discord.TextChannel]:
        # because of intermixed types in discord.py ...
        return cast(
            Optional[discord.TextChannel],  # ...this won't get much better.
            self.bot.get_channel(self.source_id),
        )

    @property
    def destinations(self) -> List[discord.TextChannel]:
        ret: List[discord.TextChannel] = []
        for idx in self.destination_ids:
            c = self.bot.get_channel(idx)
            if c:
                assert isinstance(c, discord.TextChannel)  # nosec
                ret.append(c)
        return ret

    def get_destinations(self, message: discord.Message) -> List[discord.TextChannel]:
        if message.channel.id != self.source_id:
            return []
        ret: List[discord.TextChannel] = []
        for idx in self.destination_ids:
            if idx == message.channel.id:
                continue
            c = self.bot.get_channel(idx)
            if c:
                assert isinstance(c, discord.TextChannel)  # nosec
                ret.append(c)
        return ret

    def to_data(self):
        return {"source": self.source_id, "destinations": self.destination_ids}
