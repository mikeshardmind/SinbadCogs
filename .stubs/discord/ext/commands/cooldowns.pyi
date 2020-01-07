from discord.enums import Enum

from .context import Context
from ...message import Message

from typing import Optional, TypeVar, Type

_CM = TypeVar('_CM', bound=CooldownMapping)

class BucketType(Enum):
    default: int
    user: int
    guild: int
    channel: int
    member: int
    category: int
    role: int

class Cooldown:
    rate: int
    per: float
    type: BucketType

    def __init__(self, rate: int, per: float, type: BucketType) -> None: ...
    def get_tokens(self, current: Optional[int] = ...) -> int: ...
    def update_rate_limit(self, current: Optional[float] = ...) -> Optional[float]: ...
    def reset(self) -> None: ...
    def copy(self) -> Cooldown: ...

class CooldownMapping:
    def __init__(self, original: Cooldown) -> None: ...
    def copy(self) -> CooldownMapping: ...
    @property
    def valid(self) -> bool: ...
    @classmethod
    def from_cooldown(cls: Type[_CM], rate: int, per: float, type: BucketType) -> _CM: ...
    def get_bucket(self, message: Message, current: Optional[float] = ...) -> Cooldown: ...
    def update_rate_limit(self, message: Message, current: Optional[float] = ...) -> Optional[float]: ...
