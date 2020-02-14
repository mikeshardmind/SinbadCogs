from __future__ import annotations

import contextlib
import re
from typing import NamedTuple, Union, Optional

import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.config import Config


_id_regex = re.compile(r"([0-9]{15,21})$")
_mention_regex = re.compile(r"<@!?([0-9]{15,21})>$")

SUPPORT_CHANNEL_ID = 444660866273771540
PUNISH_REACTION = "\N{BIOHAZARD SIGN}"
OWNER_IDS = (78631113035100160, 240961564503441410)
BOT_ID = 275047522026913793

PUNISH_PERMS = {
    "send_messages": False,
    "read_message_history": False,
    "add_reactions": False,
    "external_emojis": False,
}


class MentionOrID(NamedTuple):
    id: int

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str):

        match = _id_regex.match(argument) or _mention_regex.match(argument)
        if match:
            return cls(int(match.group(1)))

        raise commands.BadArgument()


class Support(commands.Cog):
    """
    Cog for managing cog support channel
    """

    def __init__(self, bot: Red):
        self.bot: Red = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_user(fuck_off=False)

    def init(self):
        """
        Reserved for future use in advance
        due to update issues with __init__ and red
        """
        pass

    def get_support_channel(self) -> Optional[discord.TextChannel]:
        c = self.bot.get_channel(SUPPORT_CHANNEL_ID)
        if not c:
            return None
        assert isinstance(c, discord.TextChannel), "mypy"  # nosec
        return c

    @checks.is_owner()
    @checks.bot_has_permissions(manage_permissions=True)
    @commands.command()
    async def supportbanish(
        self,
        ctx: commands.GuildContext,
        *,
        user_or_id: Union[discord.Member, MentionOrID],
    ):
        """ Remove a misbehaving user """
        await self.punish(user_or_id.id)
        await ctx.tick()

    async def get_message(
        self, channel: discord.TextChannel, _id: int
    ) -> Optional[discord.Message]:

        if message := discord.utils.get(self.bot.cached_messages, id=_id):
            return message

        with contextlib.suppress(discord.HTTPException):
            message = await channel.fetch_message(_id)
            return message

        return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if payload.channel_id != SUPPORT_CHANNEL_ID:
            return
        if payload.user_id not in OWNER_IDS:
            return
        if not str(payload.emoji).startswith(PUNISH_REACTION):
            return

        channel = self.get_support_channel()
        if not channel:
            return

        message = await self.get_message(channel, payload.message_id)
        if not message:
            return

        author_id = message.author.id

        await self.punish(author_id)

    async def on_message(self, message: discord.Message):
        channel = message.channel
        if not channel.id == SUPPORT_CHANNEL_ID:
            return
        assert isinstance(channel, discord.TextChannel), "mypy"  # nosec

        uid = message.author.id
        if await self.config.user_from_id(uid).fuck_off():
            if channel.permissions_for(channel.guild.me).manage_messages:
                await message.delete()
                await channel.send(
                    f"Removed message sent by someone({uid}) "
                    f"attempting to be clever and mute dodge."
                    f"\nNothing of value was lost."
                )
            await self.punish(uid)

    async def punish(self, uid: int):

        if uid in (BOT_ID, *OWNER_IDS):
            return  # let's not be an accidental idiot....

        await self.config.user_from_id(uid).fuck_off.set(True)

        channel = self.get_support_channel()
        if not channel:
            return

        overwrites = channel.overwrites
        m = channel.guild.get_member(uid)
        if not m:
            return

        auth_overwrites = overwrites.get(m, None)
        if auth_overwrites is None:
            auth_overwrites = discord.PermissionOverwrite()

        if any(k in PUNISH_PERMS and v is not False for k, v in auth_overwrites):
            auth_overwrites.update(**PUNISH_PERMS)
            await channel.set_permissions(
                m, overwrite=auth_overwrites, reason="unsupportable."
            )
