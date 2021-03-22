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

from .message import replacement_delete_messages
from .scheduler import Scheduler

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users. "
    "It does store commands provided for intended later use along "
    "with the user ID of the person who scheduled it.\n"
    "Users may delete their own data with or without making a data request."
)


async def setup(bot):
    # Next line *does* work as intended. Mypy just hates it (see __slots__ use for why)
    discord.TextChannel.delete_messages = replacement_delete_messages  # type: ignore
    cog = Scheduler(bot)
    bot.add_cog(cog)
    cog.init()
