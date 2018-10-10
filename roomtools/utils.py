import discord
from typing import Union, Dict, Optional, Any

OverwriteDict = Dict[Union[discord.Role, discord.Member], discord.PermissionOverwrite]


class ChannelCreation:
    """
    This really shouldn't be needed,
    but until/unless I drop Redbot and discord.py for a custom base and lib
    I'll continue dealing with the fact that discord.py
    doesn't allow all the args discord does on channel creation
    and that the lib maintainer is unresponsive on issues and PRs
    """

    @staticmethod
    async def _create_channel(
        guild: discord.Guild,
        name: str,
        *,
        channel_type: discord.ChannelType,
        overwrites: Optional[OverwriteDict] = None,
        category: Optional[discord.CategoryChannel] = None, 
        reason: Optional[str] = None,
        topic: Optional[str] = None,
        bitrate: Optional[int] = None,
        user_limit: Optional[int] = None,
        rate_limit_per_user: Optional[int] = None,
        nsfw: Optional[bool] = None
    ):

        overwrites = overwrites or {}
        parent_id = category.id if category else None

        perms = []
        for target, perm in overwrites.items():
            allow, deny = perm.pair()
            ow = {
                'allow': allow.value,
                'deny': deny.value,
                'id': target.id
            }
            if isinstance(target, discord.Role):
                ow['type'] = 'role'
            else:
                ow['type'] = 'member'
            perms.append(ow)

        payload = {
            'name': name,
            'type': channel_type.value,
            'permission_overwrites': perms or None,
            'parent_id': parent_id,
            'topic': topic,
            'bitrate': bitrate,
            'user_limit': user_limit,
            'rate_limit_per_user': rate_limit_per_user,
            'nsfw': nsfw,
        }

        payload = {k: v for k, v in payload.items() if v is not None}

        data = await guild._state.http.request(
            discord.http.Route(
                method='POST', path='/guilds/{guild_id}/channels', guild_id=guild.id
            ),
            json=payload,
            reason=reason,
        )

        channel_class: Any = {
            discord.ChannelType.category.value: discord.CategoryChannel,
            discord.ChannelType.text.value: discord.TextChannel,
            discord.ChannelType.voice.value: discord.VoiceChannel,
        }.get(channel_type.value)

        channel = channel_class(state=guild._state, guild=guild, data=data)
        guild._channels[channel.id] = channel
        return channel