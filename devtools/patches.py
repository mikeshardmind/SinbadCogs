import discord
from redbot.core.bot import Red


class StableMentions(discord.AllowedMentions):
    """ Because despite bringing it up multiple times, a property wasn't used """

    @property  # type: ignore
    def everyone(self):
        return False

    @everyone.setter
    def everyone(self, value):
        return

    @property  # type: ignore
    def roles(self):
        return False

    @roles.setter
    def roles(self, value):
        return


patch_bot_restore = None


def patch_bot(bot):

    obj = StableMentions()

    def getter(self):
        return obj

    def setter(self, val):
        return

    global patch_bot_restore
    patch_bot_restore = getattr(Red, "allowed_mentions", None)
    bot.allowed_mentions = obj
    setattr(Red, "allowed_mentions", property(getter, setter))


def remove_patches(bot):
    global patch_bot_restore
    if patch_bot_restore:
        setattr(Red, "allowed_mentions", patch_bot_restore)
    bot.allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)
