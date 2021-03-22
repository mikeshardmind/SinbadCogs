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


from .core import RoleManagement

__red_end_user_data_statement__ = (
    "This cog does not persistently store end user data. "
    "This cog does store discord IDs as needed for operation."
)


async def setup(bot):
    cog = RoleManagement(bot)
    bot.add_cog(cog)
    cog.init()
