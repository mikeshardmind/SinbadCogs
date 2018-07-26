# https://github.com/python/mypy/issues/1996

from abc import ABC, abstractmethod
from typing import List

import discord


class RoleMeta(ABC):
    """
    Metaclass for well behaved mixin.
    """

    @abstractmethod
    def config(self):
        raise NotImplementedError()

    @abstractmethod
    def bot(self):
        raise NotImplementedError()
    
    @abstractmethod
    def is_self_assign_eligible(who: discord.Member, role: discord.Role) -> List[discord.Role]:
        raise NotImplementedError()

    @abstractmethod
    def update_roles_atomically(
        self,
        *,
        who: discord.Member,
        give: List[discord.Role] = None,
        remove: List[discord.Role] = None,
    ):
        raise NotImplementedError()

