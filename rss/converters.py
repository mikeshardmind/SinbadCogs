from typing import Optional
from redbot.core import commands

from redbot.core.i18n import Translator

_ = Translator("This doesn't even actually matter anymore.", __file__)


def tristate(arg: str) -> Optional[bool]:
    if arg.lower() in ("true", "yes"):
        return True
    if arg.lower() in ("false", "no"):
        return False
    if arg.lower() in ("none", "default"):
        return None
    raise commands.BadArgument(
        _(
            '"{arg}" is not a valid setting.'
            ' Valid settings are "true" or "false", or "default" to '
            "remove the setting"
        ).format(arg=arg)
    )
