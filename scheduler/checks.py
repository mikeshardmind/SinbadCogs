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
