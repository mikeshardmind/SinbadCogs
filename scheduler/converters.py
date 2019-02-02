import argparse
import shlex
from typing import Optional, Tuple
from datetime import datetime, timedelta
from redbot.core.commands import Context, BadArgument, Converter

from .time_utils import parse_time, parse_timedelta

class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class Schedule(Converter):

    async def convert(self, ctx: Context, argument: str) -> Tuple[datetime, Optional[timedelta]]:

        start: datetime
        recur: Optional[timedelta] = None

        parser = NoExitParser(description="Scheduler event parsing", add_help=False)
        parser.add_argument("--every", nargs="*", dest="every", default=[])
        at_or_in = parser.add_mutually_exclusive_group()
        at_or_in.add_argument("--start-at", nargs="*", dest="at", default=[])
        at_or_in.add_argument("--start-in", nargs="*", dest="in", default=[])

        try:
            vals = vars(parser.parse_args(shlex.split(argument)))
        except Exception as exc:
            raise BadArgument() from exc

        if not vals['at'] or vals ['in']:
            raise BadArgument("You must provide one of `--start-in` of `--start-at`")

        for delta in ("in", "every"):
            if vals[delta]:
                parsed = parse_timedelta(" ".join(vals[delta]))
                if not parsed:
                    raise BadArgument("I couldn't understand that time interval")
                else:
                    if delta == "in":
                        start = datetime.utcnow() + parsed
                    else:
                        recur = parsed
                        if recur.total_seconds() < 60:
                            raise BadArgument(
                                "You can't schedule something to happen that frequently, "
                                "I'll get ratelimited."
                            )

        if vals['at']:
            try:
                start = parse_time(" ".join(vals["at"]))
            except Exception:
                raise BadArgument("I couldn't understand that starting time.") from None

        return start, recur
