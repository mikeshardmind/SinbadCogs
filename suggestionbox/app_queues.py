from enum import IntEnum
from typing import Callable, List, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_extensions import KwArg
else:
    KwArg = lambda: Any


Vote = Tuple[int, "Action"]
VoteList = List[Vote]
FormulaType = Callable[[VoteList, KwArg()], "Action"]


class Action(IntEnum):
    NOOP = 0
    REJECT = 1
    APPROVE = 2


class State(IntEnum):
    PENDING = 0
    STALE = 1
    REJECTED = 2
    APPROVED = 3


class Formulas:

    AVAILABLE = ("difference", "threshold", "majority")

    @classmethod
    def fetch(cls, key: str) -> FormulaType:
        f: FormulaType = getattr(cls, key)
        return f

    @staticmethod
    def threshold(
        votes: VoteList, *, threshold: int, eligible: List[int], **kwargs
    ) -> Action:

        yays, nays = 0, 0
        for _who, vote in votes:
            if vote == Action.APPROVE:
                yays += 1
                if yays >= threshold:
                    return Action.APPROVE
            elif vote == Action.REJECT:
                nays += 1
                if nays >= threshold:
                    return Action.REJECT
        return Action.NOOP

    @staticmethod
    def difference(
        votes: VoteList, *, threshold: int, eligible: List[int], **kwargs
    ) -> Action:

        approve_at = threshold
        reject_at = 0 - threshold
        diff = 0

        for _who, vote in votes:
            if vote == Action.APPROVE:
                diff += 1
                if diff >= approve_at:
                    return Action.APPROVE
            elif vote == Action.REJECT:
                diff -= 1
                if diff <= reject_at:
                    return Action.REJECT
        return Action.NOOP

    @staticmethod
    def majority(votes: VoteList, *, eligible: List[int], **kwargs) -> Action:

        req = len(eligible) // 2 + 1
        yays, nays = 0, 0

        for who, vote in votes:
            if who not in eligible:
                continue

            if vote == Action.APPROVE:
                yays += 1
                if yays >= req:
                    return Action.APPROVE
            elif vote == Action.REJECT:
                nays += 1
                if nays >= req:
                    return Action.REJECT
        return Action.NOOP
