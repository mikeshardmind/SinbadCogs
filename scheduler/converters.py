from __future__ import annotations

import argparse
import dataclasses
from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Optional, Tuple

from redbot.core.commands import BadArgument, Context

from .time_utils import parse_time, parse_timedelta


class NonNumeric(NamedTuple):
    parsed: str

    @classmethod
    async def convert(cls, context: Context, argument: str):
        if argument.isdigit():
            raise BadArgument("Event names must contain at least 1 non-numeric value")
        return cls(argument)


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


@dataclasses.dataclass()
class Schedule:
    start: datetime
    command: str
    recur: Optional[timedelta] = None
    quiet: bool = False

    def to_tuple(self) -> Tuple[str, datetime, Optional[timedelta]]:
        return self.command, self.start, self.recur

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        start: datetime
        command: Optional[str] = None
        recur: Optional[timedelta] = None

        # Blame iOS smart punctuation,
        # and end users who use it for this (minor) perf loss
        argument = argument.replace("—", "--")

        command, *arguments = argument.split(" -- ")
        if arguments:
            argument = " -- ".join(arguments)
        else:
            command = None

        parser = NoExitParser(description="Scheduler event parsing", add_help=False)
        parser.add_argument(
            "-q", "--quiet", action="store_true", dest="quiet", default=False
        )
        parser.add_argument("--every", nargs="*", dest="every", default=[])
        if not command:
            parser.add_argument("command", nargs="*")
        at_or_in = parser.add_mutually_exclusive_group()
        at_or_in.add_argument("--start-at", nargs="*", dest="at", default=[])
        at_or_in.add_argument("--start-in", nargs="*", dest="in", default=[])

        try:
            vals = vars(parser.parse_args(argument.split(" ")))
        except Exception as exc:
            raise BadArgument() from exc

        if not (vals["at"] or vals["in"]):
            raise BadArgument("You must provide one of `--start-in` or `--start-at`")

        if not command and not vals["command"]:
            raise BadArgument("You have to provide a command to run")

        command = command or " ".join(vals["command"])

        for delta in ("in", "every"):
            if vals[delta]:
                parsed = parse_timedelta(" ".join(vals[delta]))
                if not parsed:
                    raise BadArgument("I couldn't understand that time interval")

                if delta == "in":
                    start = datetime.now(timezone.utc) + parsed
                else:
                    recur = parsed
                    if recur.total_seconds() < 60:
                        raise BadArgument(
                            "You can't schedule something to happen that frequently, "
                            "I'll get ratelimited."
                        )

        if vals["at"]:
            try:
                start = parse_time(" ".join(vals["at"]))
            except Exception:
                raise BadArgument("I couldn't understand that starting time.") from None

        return cls(command=command, start=start, recur=recur, quiet=vals["quiet"])


class TempMute(NamedTuple):
    reason: Optional[str]
    start: datetime

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        start: datetime
        reason: str

        # Blame iOS smart punctuation,
        # and end users who use it for this (minor) perf loss
        argument = argument.replace("—", "--")

        parser = NoExitParser(description="Scheduler event parsing", add_help=False)
        parser.add_argument("reason", nargs="*")
        at_or_in = parser.add_mutually_exclusive_group()
        at_or_in.add_argument("--until", nargs="*", dest="until", default=[])
        at_or_in.add_argument("--for", nargs="*", dest="for", default=[])

        try:
            vals = vars(parser.parse_args(argument.split()))
        except Exception as exc:
            raise BadArgument() from exc

        if not (vals["until"] or vals["for"]):
            raise BadArgument("You must provide one of `--until` or `--for`")

        reason = " ".join(vals["reason"])

        if vals["for"]:
            parsed = parse_timedelta(" ".join(vals["for"]))
            if not parsed:
                raise BadArgument("I couldn't understand that time interval")
            start = datetime.now(timezone.utc) + parsed

        if vals["until"]:
            try:
                start = parse_time(" ".join(vals["at"]))
            except Exception:
                raise BadArgument("I couldn't understand that unmute time.") from None

        return cls(reason, start)
