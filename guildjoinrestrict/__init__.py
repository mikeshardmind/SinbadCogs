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

from .core import GuildJoinRestrict

__red_end_user_data_statement__ = (
    "This cog persistently stores the minimum "
    "amount of data needed to restrict guild joins to those allowed by settings. "
    "It will not respect data deletion by end users, nor can end users request "
    "their data from this cog since it only stores "
    "discord IDs and whether those IDs are allowed or denied. "
    "Discord IDs may occasionally be logged to a file as needed for audit purposes."
)


async def setup(bot):
    cog = GuildJoinRestrict(bot)
    bot.add_cog(cog)
    cog.init()
