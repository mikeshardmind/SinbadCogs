from enum import Enum as Enum
from typing import Union, TypeVar, Type, overload

# Technically, these enumerations do not inherit from enum.Enum, but because type checking
# does something special for enum.Enum and discord.enums.Enum is a drop-in replacement for
# enum.Enum, typings are using enum.Enum directly

class ChannelType(Enum):
    text: int
    private: int
    voice: int
    group: int
    category: int
    news: int
    store: int

class MessageType(Enum):
    default: int
    recipient_add: int
    recipient_remove: int
    call: int
    channel_name_change: int
    channel_icon_change: int
    pins_add: int
    new_member: int
    premium_guild_subscription: int
    premium_guild_tier_1: int
    premium_guild_tier_2: int
    premium_guild_tier_3: int
    channel_follow_add: int

class VoiceRegion(Enum):
    us_west: str
    us_east: str
    us_south: str
    us_central: str
    eu_west: str
    eu_central: str
    singapore: str
    london: str
    sydney: str
    amsterdam: str
    frankfurt: str
    brazil: str
    hongkong: str
    russia: str
    japan: str
    southafrica: str
    india: str
    europe: str
    vip_us_east: str
    vip_us_west: str
    vip_amsterdam: str

class SpeakingState(Enum):
    none: int
    voice: int
    soundshare: int
    priority: int
    def __int__(self) -> int: ...

class VerificationLevel(Enum):
    none: int
    low: int
    medium: int
    high: int
    table_flip: int
    extreme: int
    double_table_flip: int
    def __lt__(self, other) -> bool: ...
    def __gt__(self, other) -> bool: ...
    def __eq__(self, other) -> bool: ...
    def __int__(self) -> int: ...

class ContentFilter(Enum):
    disabled: int
    no_role: int
    all_members: int

class UserContentFilter(Enum):
    disabled: int
    friends: int
    all_messages: int

class FriendFlags(Enum):
    noone: int
    mutual_guilds: int
    mutual_friends: int
    guild_and_friends: int
    everyone: int

class Theme(Enum):
    light: str
    dark: str

class Status(Enum):
    online: str
    offline: str
    idle: str
    dnd: str
    do_not_disturb: str
    invisible: str

class DefaultAvatar(Enum):
    blurple: int
    grey: int
    gray: int
    green: int
    orange: int
    red: int

class RelationshipType(Enum):
    friend: int
    blocked: int
    incoming_request: int
    outgoing_request: int

class NotificationLevel(Enum):
    all_messages: int
    only_mentions: int

class AuditLogActionCategory(Enum):
    create: int
    delete: int
    update: int

class AuditLogAction(Enum):
    guild_update: int
    channel_create: int
    channel_update: int
    channel_delete: int
    overwrite_create: int
    overwrite_update: int
    overwrite_delete: int
    kick: int
    member_prune: int
    ban: int
    unban: int
    member_update: int
    member_role_update: int
    role_create: int
    role_update: int
    role_delete: int
    invite_create: int
    invite_update: int
    invite_delete: int
    webhook_create: int
    webhook_update: int
    webhook_delete: int
    emoji_create: int
    emoji_update: int
    emoji_delete: int
    message_delete: int
    @property
    def category(self) -> AuditLogActionCategory: ...
    @property
    def target_type(self) -> str: ...

class UserFlags(Enum):
    staff: int
    partner: int
    hypesquad: int
    bug_hunter: int
    hypesquad_bravery: int
    hypesquad_brilliance: int
    hypesquad_balance: int
    early_supporter: int

class ActivityType(Enum):
    unknown: int
    playing: int
    streaming: int
    listening: int
    watching: int
    def __int__(self) -> int: ...

class HypeSquadHouse(Enum):
    bravery: int
    brilliance: int
    balance: int

class PremiumType(Enum):
    nitro_classic: int
    nitro: int

class TeamMembershipState(Enum):
    invited: int
    accepted: int

_EnumType = TypeVar("_EnumType", bound=Enum)
@overload
def try_enum(cls: Type[_EnumType], val: _EnumType) -> _EnumType: ...
@overload
def try_enum(cls: Type[_EnumType], val: int) -> Union[_EnumType, int]: ...
@overload
def try_enum(cls: Type[_EnumType], val: str) -> Union[_EnumType, str]: ...
