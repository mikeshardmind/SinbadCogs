import discord
from redbot.core import commands

SUPPORT_CHANNEL_ID = 444660866273771540
PUNISH_REACTION = "\N{BIOHAZARD SIGN}"
OWNER_ID = 78631113035100160
BOT_ID = 275047522026913793

PUNISH_PERMS = {
    "send_messages": False,
    "read_message_history": False,
    "add_reactions": False,
    "external_emojis": False,
}


class Management(commands.Cog):
    """
    Management shit.
    """

    def __init__(self, bot):
        self.bot = bot

    async def get_message(self, channel: discord.TextChannel, _id: int):

        message = next(
            filter(lambda m: m.id == _id, channel.guild._state._messages), None
        )
        if message:
            return message
        try:
            message = await channel.get_message(_id)
        except discord.HTTPException:
            return None
        else:
            return message

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        if not payload.channel_id == SUPPORT_CHANNEL_ID:
            return
        if not payload.user_id == OWNER_ID:
            return
        if not str(payload.emoji) == PUNISH_REACTION:
            return

        channel = self.bot.get_channel(SUPPORT_CHANNEL_ID)
        message = await self.get_message(channel, payload.message_id)
        author = message.author
        if author.id in (OWNER_ID, BOT_ID):
            return  # let's not be an accidental idiot....

        overwrites = channel.overwrites

        auth_overwrites = next(filter(lambda o: o[0] == author, overwrites), (None, None))[1]
        if auth_overwrites is None:
            auth_overwrites = discord.PermissionOverwrite()

        if any(k in PUNISH_PERMS and v is not False for k, v in auth_overwrites):
            auth_overwrites.update(**PUNISH_PERMS)
            await channel.set_permissions(
                author, overwrite=auth_overwrites, reason="unsupportable."
            )
