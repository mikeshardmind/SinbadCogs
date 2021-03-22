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

import datetime
import re

import discord
from redbot.core import commands
from redbot.core.bot import Red


class MentionHelp(commands.Cog):
    """
    Provide help to people who mention the bot
    """

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return

    def __init__(self, bot):
        self.bot: Red = bot
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

        if not await self.bot.message_eligible_as_command(message):
            return

        if guild:
            if await self.bot.cog_disabled_in_guild_raw(self.qualified_name, guild.id):
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
