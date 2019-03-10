from enum import IntEnum
from typing import Callable, List, Tuple, Dict, TypeVar

Vote = Tuple[int, "Action"]
VoteList = List[Vote]
FormulaType = Callable[[VoteList, int], "Action"]


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

    AVAILABLE = ("difference", "threshold")

    @classmethod
    def fetch(cls, key: str) -> FormulaType:
        f: FormulaType = getattr(cls, key)
        return f

    @staticmethod
    def threshold(votes: VoteList, threshold: int) -> Action:
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
    def difference(votes: VoteList, difference: int) -> Action:
        approve_at = difference
        reject_at = 0 - difference
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
