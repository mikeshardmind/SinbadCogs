# https://github.com/python/mypy/issues/1996

from abc import ABC, abstractmethod
from typing import List, no_type_check

import discord


class MixinMeta(ABC):
    """
    Metaclass for well behaved type hint detection with composite class.
    """

    @no_type_check
    @abstractmethod
    def config(self):
        raise NotImplementedError()

    @no_type_check
    @abstractmethod
    def bot(self):
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
        give: List[discord.Role] = None,
        remove: List[discord.Role] = None,
    ):
        raise NotImplementedError()

    @abstractmethod
    def all_are_valid_roles(self, ctx, *roles: discord.Role) -> bool:
        raise NotImplementedError()
