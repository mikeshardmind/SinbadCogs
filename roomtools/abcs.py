import abc

from redbot.core.bot import Red
from redbot.core.config import Config


class MixedMeta(abc.ABC):
    """
    mypy is nice, but I need this for it to shut up about composite classes.
    """

    def __init__(self, *args):
        self.bot: Red
        self._antispam: dict
        self.antispam_intervals: list
        self.tmpc_config: Config
        self.ar_config: Config
