import datetime
import re

import discord
from redbot.core import commands


class MentionHelp(commands.Cog):
    """
    Provide help to people who mention the bot
    """

    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )

    def __init__(self, bot):
        self.bot = bot
        self.mention_pattern = None
        self.cooldowns = commands.CooldownMapping.from_cooldown(
            1, 300, commands.BucketType.channel
        )

    def init(self):
        pass

    # for later configuration, included now to prevent issues with red's hotreload.

    @commands.Cog.listener("on_message_without_command")
    async def help_handler(self, message: discord.Message):

        if self.mention_pattern is None:
            self.mention_pattern = re.compile(rf"^<@!?{self.bot.user.id}>$")

        if not self.mention_pattern.match(message.content):
            return

        channel = message.channel
        guild = message.guild

        if guild:
            assert isinstance(channel, discord.TextChannel)  # nosec
            if not channel.permissions_for(guild.me).send_messages:
                return
            if not (await self.bot.ignored_channel_or_guild(message)):
                return
                # This is *supposed* to only take a context object,
                # ducktyping is safe here though

        if not (await self.bot.allowed_by_whitelist_blacklist(message.author)):
            return

        bucket = self.cooldowns.get_bucket(message)
        current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()

        if bucket.update_rate_limit(current):
            return

        prefixes = await self.bot.get_valid_prefixes(guild)
        # avoids using the mention form if --mentionable is in use
        command = discord.utils.escape_markdown(f"{prefixes[-1]}help")
        destination = channel if guild else message.author

        await destination.send(
            "Hi there, it appears that you may need some assistance.\n"
            "If this is accurate use the following for help:\n"
            f"{command}\n\n"
            "This message was shown due to a mention of the bot without "
            "further interaction and will not resend in this channel "
            "for at least 5 minutes"
        )

        # TODO: Setting governing the below:
        # await bot.send_help_for_context(bot)
        # needs a fake context object OR
        # a required support for invoking help without context
        # <https://github.com/Cog-Creators/Red-DiscordBot/pull/4011#issuecomment-649865028>
        # for some more detail on this.
