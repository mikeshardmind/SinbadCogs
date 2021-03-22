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


from .modnotes import ModNotes

__red_end_user_data_statement__ = (
    "This cog stores data provided to it for "
    "the purpose of a permanent moderation note system. "
    "\nThis cog does not currently respect the data APIs and bot "
    "owners may need to handle data deletion requests for it manually, "
    "but they will be given notice in such cases."
)


async def setup(bot):
    cog = ModNotes(bot)
    bot.add_cog(cog)
    cog.init()
