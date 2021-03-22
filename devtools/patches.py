#   Copyright 2017-present Michael Hall
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

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
