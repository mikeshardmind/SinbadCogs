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

from .core import SuggestionBox

__red_end_user_data_statement__ = (
    "This cog stores data provided to it by command as needed for operation. "
    "As this data is for suggestions to be given from a user to a community, "
    "it is not reasonably considered end user data and will "
    "not be deleted except as required by Discord."
)


async def setup(bot):
    bot.add_cog(SuggestionBox(bot))
