from jinja2.sandbox import ImmutableSandboxedEnvironment

import discord
from redbot.core import commands

from types import SimpleNamespace

SAFER_ATTRS = SimpleNamespace(
    context=(
        "author",
        "channel",
        "clean_prefix",
        "guild",
        "me",
        "prefix",
        "permission_state",
    ),
    usermember=(
        "roles",
        "top_role",
        "guild_permissions",
        "guild",
        "name",
        "id",
        "avatar",
        "color",
        "colour",
        "created_at",
        "discriminator",
        "display_name",
        "mention",
        "joined_at",
    ),
    channel=(
        "name",
        "topic",
        "guild",
        "id",
        "mention",
        "position",
        "category",
        "category_id",
        "members",
        "nsfw",
        "overwrites",
        "permissions_for",
        "type",
    ),
    role=(
        "color",
        "colour",
        "id",
        "created_at",
        "managed",
        "members",
        "mention",
        "mentionable",
        "name",
        "permissions",
        "position",
    ),
    guild=(
        "afk_channel",
        "afk_timeout",
        "banner",
        "bitrate_limit",
        "categories",
        "channels",
        "chunked",
        "created_at",
        "default_notifications",
        "default_role",
        "description",
        "emoji_limit",
        "emojis",
        "explicit_content_filter",
        "features",
        "filesize_limit",
        "get_channel",
        "get_member",
        "get_role",
        "icon",
        "id",
        "large",
        "me",
        "member_count",
        "members",
        "mfa_level",
        "name",
        "owner",
        "owner_id",
        "premium_subscription_count",
        "premium_tier",
        "region",
        "roles",
        "splash",
        "system_channel",
        "system_channel_flags",
        "text_channels",
        "verification_level",
        "voice_channels",
    ),
    permissions=(
        "add_reactions",
        "administrator",
        "attach_files",
        "ban_members",
        "change_nickname",
        "connect",
        "create_instant_invite",
        "deafen_members",
        "embed_links",
        "external_emojis",
        "kick_members",
        "manage_channels",
        "manage_emojis",
        "manage_guild",
        "manage_messages",
        "manage_nicknames",
        "manage_roles",
        "manage_webhooks",
        "mention_everyone",
        "move_members",
        "mute_members",
        "priority_speaker",
        "read_message_history",
        "read_messages",
        "send_messages",
        "send_tts_messages",
        "speak",
        "stream",
        "use_voice_activation",
        "view_audit_log",
    ),
)

# Shouldn't be possible to reach these with above rules,
# but a small bit of extra precaution won't hurt.
BLACKLISTED_TYPES = (
    discord.Client,
    discord.http.HTTPClient,
    discord.shard.Shard,
    discord.gateway.DiscordWebSocket,
    commands.Cog,
    commands.Command,
)


class RestrictedEnv(ImmutableSandboxedEnvironment):
    intercepted_binops = frozenset(["//", "%", "+", "*", "-", "/", "**"])
    intercepted_unops = frozenset(["-", "+"])

    def is_safe_attribute(self, obj, attr, value):
        for obj_type, allowed in (
            (commands.Context, SAFER_ATTRS.context),
            ((discord.User, discord.Member), SAFER_ATTRS.usermember),
            (discord.Role, SAFER_ATTRS.role),
            ((discord.abc.GuildChannel, discord.DMChannel), SAFER_ATTRS.channel),
            (discord.Guild, SAFER_ATTRS.guild),
            (
                (discord.Permissions, discord.PermissionOverwrite),
                SAFER_ATTRS.permissions,
            ),
        ):
            if isinstance(obj, obj_type) and attr not in allowed:
                return False

        if isinstance(obj, BLACKLISTED_TYPES):
            return False

        return super().is_safe_attribute(obj, attr, value)

    def call_binop(self, context, operator, left, right):
        return self.undefined("You can't use operators here")

    def call_unop(self, context, operator, arg):
        return self.undefined("You can't use operators here")
