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

from abc import ABC, abstractmethod
from typing import List, Optional

import discord
from redbot.core import Config
from redbot.core.bot import Red


class MixinMeta(ABC):
    """
    Metaclass for well behaved type hint detection with composite class.
    """

    # https://github.com/python/mypy/issues/1996

    qualified_name: str

    def __init__(self, *_args):
        self.config: Config
        self.bot: Red

    @abstractmethod
    def strip_variations(self, s: str) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def wait_for_ready(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def is_self_assign_eligible(
        self, who: discord.Member, role: discord.Role
    ) -> List[discord.Role]:
        raise NotImplementedError()

    @abstractmethod
    async def update_roles_atomically(
        self,
        *,
        who: discord.Member,
        give: Optional[List[discord.Role]] = None,
        remove: Optional[List[discord.Role]] = None,
    ):
        raise NotImplementedError()

    @abstractmethod
    async def all_are_valid_roles(self, ctx, *roles: discord.Role) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def maybe_update_guilds(self, *guilds: discord.Guild) -> None:
        raise NotImplementedError()

    @abstractmethod
    def get_top_role(self, member: discord.Member) -> discord.Role:
        raise NotImplementedError()
