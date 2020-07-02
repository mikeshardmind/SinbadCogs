import functools
from redbot.core.bot import Red

import discord


async def message_is_eligible_as_command(bot: Red, message: discord.Message) -> bool:
    """
    Runs through the things which apply globally about commands
    to determine if a message may be responded to as a command.

    This can't interact with permissions as permissions is hyper-local
    with respect to command objects, create command objects for this
    if that's needed.

    This also does not check for prefix or command conflqicts,
    is primarily designed for non-prefix based response handling
    via on_message_without_command
    """

    channel = message.channel
    guild = message.guild

    if guild:
        assert isinstance(channel, discord.TextChannel)  # nosec
        if not channel.permissions_for(guild.me).send_messages:
            return False
        if not (await bot.ignored_channel_or_guild(message)):
            return False
            # This is *supposed* to only take a context object,
            # ducktyping is safe here though

    if not (await bot.allowed_by_whitelist_blacklist(message.author)):
        return False

    return True


def ensure_allowed_as_command(f):
    """
    Decorator to be applied to a cog method
    which takes a message as it's only argument,
    cog *must* have self.bot as a reference to the bot
    """

    @functools.wraps(f)
    async def wrapped(cog_class, message):

        bot = cog_class.bot
        if await message_is_eligible_as_command(bot, message):
            await f(cog_class, message)

    return wrapped
