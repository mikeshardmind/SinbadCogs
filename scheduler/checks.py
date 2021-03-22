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

from __future__ import annotations

from redbot.core import commands


def can_run_command(command_name: str):
    async def predicate(ctx):

        command = ctx.bot.get_command(command_name)
        if not command:
            return False

        try:
            can_run = await command.can_run(
                ctx, check_all_parents=True, change_permission_state=False
            )
        except commands.CommandError:
            can_run = False

        return can_run

    return commands.check(predicate)
