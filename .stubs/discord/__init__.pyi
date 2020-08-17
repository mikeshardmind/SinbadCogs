from typing import NamedTuple

from typing_extensions import Final

from . import abc as abc
from . import opus as opus
from . import utils as utils
from .activity import *
from .appinfo import AppInfo as AppInfo
from .asset import Asset as Asset
from .audit_logs import AuditLogChanges as AuditLogChanges
from .audit_logs import AuditLogDiff as AuditLogDiff
from .audit_logs import AuditLogEntry as AuditLogEntry
from .calls import CallMessage as CallMessage
from .calls import GroupCall as GroupCall
from .channel import *
from .client import Client as Client
from .colour import Color as Color
from .colour import Colour as Colour
from .embeds import Embed as Embed
from .emoji import Emoji as Emoji
from .emoji import PartialEmoji as PartialEmoji
from .enums import *
from .errors import *
from .file import File as File
from .guild import Guild as Guild
from .guild import SystemChannelFlags as SystemChannelFlags
from .invite import Invite as Invite
from .member import Member as Member
from .member import VoiceState as VoiceState
from .mentions import AllowedMentions as AllowedMentions
from .message import Attachment as Attachment
from .message import Message as Message
from .object import Object as Object
from .permissions import PermissionOverwrite as PermissionOverwrite
from .permissions import Permissions as Permissions
from .player import *
from .raw_models import *
from .reaction import Reaction as Reaction
from .relationship import Relationship as Relationship
from .role import Role as Role
from .shard import AutoShardedClient as AutoShardedClient
from .team import *
from .user import ClientUser as ClientUser
from .user import Profile as Profile
from .user import User as User
from .voice_client import VoiceClient as VoiceClient
from .webhook import *
from .widget import Widget as Widget
from .widget import WidgetChannel as WidgetChannel
from .widget import WidgetMember as WidgetMember

class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int

__title__: Final[str] = ...
__author__: Final[str] = ...
__license__: Final[str] = ...
__copyright__: Final[str] = ...
__version__: Final[str] = ...
version_info: Final[VersionInfo] = ...
