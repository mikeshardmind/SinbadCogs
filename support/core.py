import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red

SUPPORT_CHANNEL_ID = 444660866273771540
PUNISH_REACTION = "\N{BIOHAZARD SIGN}"
OWNER_IDS = (78631113035100160, 240961564503441410)
BOT_ID = 275047522026913793

PUNISH_PERMS = 329792


class Support(commands.Cog, qualified_name="Sinbad's Support Toolbox"):
    """
    Shhhhhhh.
    """

    def __init__(self, bot: Red):
        self.bot: Red = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if (
            message.author.id in (BOT_ID, *OWNER_IDS)
            or message.channel.id != SUPPORT_CHANNEL_ID
        ):
            return

        for u in message.mentions:
            if u.id in OWNER_IDS:
                r = discord.http.Route(
                    "POST",
                    "/channels/{channel_id}/messages",
                    channel_id=message.channel.id,
                )

                kwargs = {
                    "allowed_mentions": {"parse": []},
                    "content": f"Please refrain from mentioning. {message.author.mention}",
                }  # This will prevent it from pinging, but leave a record in the chat.

                return await self.bot.http.request(r, json=kwargs)  # type: ignore

    async def get_message(self, channel: discord.TextChannel, _id: int):

        message = next(filter(lambda m: m.id == _id, self.bot.cached_messages), None)
        if message:
            return message
        try:
            message = await channel.fetch_message(_id)
        except discord.HTTPException:
            return None
        else:
            return message

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if not payload.channel_id == SUPPORT_CHANNEL_ID:
            return
        if payload.user_id not in OWNER_IDS:
            return
        if PUNISH_REACTION not in str(payload.emoji):
            return

        if not (channel := self.bot.get_channel(SUPPORT_CHANNEL_ID)):
            return

        assert isinstance(channel, discord.TextChannel)  # nosec
        message = await self.get_message(channel, payload.message_id)
        if not message:
            return

        author = message.author
        if author.id in (BOT_ID, *OWNER_IDS):
            return
        if channel.permissions_for(author).value & PUNISH_PERMS:
            overwrites = channel.overwrites

            auth_overwrites = overwrites.get(author, None)
            if auth_overwrites is None:
                auth_overwrites = discord.PermissionOverwrite()

            allow, deny = auth_overwrites.pair()
            allow.value = allow.value & ~PUNISH_PERMS
            deny.value = deny.value | PUNISH_PERMS
            auth_overwrites = discord.PermissionOverwrite.from_pair(allow, deny)

            await channel.set_permissions(
                author, overwrite=auth_overwrites, reason="Emoji Mute."
            )
