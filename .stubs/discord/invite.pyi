import datetime

from .mixins import Hashable
from .guild import Guild
from .user import User
from .channel import TextChannel, VoiceChannel, StoreChannel
from .enums import ChannelType, VerificationLevel
from .asset import Asset

from typing import Optional, Union, NamedTuple, List, Set
from typing_extensions import Literal

_VALID_ICON_FORMATS = Literal['jpeg', 'jpg', 'webp', 'png']

class PartialInviteChannel(NamedTuple):
    id: int
    name: str
    type: ChannelType

    @property
    def mention(self) -> str: ...
    @property
    def created_at(self) -> datetime.datetime: ...

class PartialInviteGuild:
    features: List[str]
    icon: Optional[str]
    banner: Optional[str]
    id: int
    name: str
    splash: Optional[str]
    verification_level: VerificationLevel
    description: Optional[str]

    @property
    def created_at(self) -> datetime.datetime: ...
    @property
    def icon_url(self) -> Asset: ...
    def icon_url_as(self, *, format: _VALID_ICON_FORMATS = ..., size: int = ...) -> Asset: ...
    @property
    def banner_url(self) -> Asset: ...
    def banner_url_as(self, *, format: _VALID_ICON_FORMATS = ..., size: int = ...) -> Asset: ...
    @property
    def splash_url(self) -> Asset: ...
    def splash_url_as(self, *, format: _VALID_ICON_FORMATS = ..., size: int = ...) -> Asset: ...

class Invite(Hashable):
    max_age: int
    code: str
    guild: Union[Guild, PartialInviteGuild]
    revoked: bool
    created_at: datetime.datetime
    temporary: bool
    uses: int
    max_uses: int
    inviter: User
    approximate_member_count: Optional[int]
    approximate_presence_count: Optional[int]
    channel: Union[TextChannel, VoiceChannel, StoreChannel, PartialInviteChannel]

    def __hash__(self) -> int: ...
    @property
    def id(self) -> str: ...
    @property
    def url(self) -> str: ...
    async def delete(self, *, reason: Optional[str] = ...) -> None: ...
