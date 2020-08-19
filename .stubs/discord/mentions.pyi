from typing import Any, Iterable, List, Union
from typing_extensions import TypedDict

import discord.abc

ItSnow = Iterable[discord.abc.Snowflake]

class _MentionsDictBase(TypedDict):
    parse: List[str]

class _MentionsDict(_MentionsDictBase, total=False):
    users: List[int]
    roles: List[int]

class AllowedMentions:
    everyone: bool
    users: Union[bool, ItSnow]
    roles: Union[bool, ItSnow]
    def __init__(
        self,
        *,
        everyone: Union[bool] = ...,
        users: Union[bool, ItSnow] = ...,
        roles: Union[bool, ItSnow] = ...,
    ) -> None: ...
    def to_dict(self) -> _MentionsDict: ...
    def merge(self, other: AllowedMentions) -> AllowedMentions: ...
