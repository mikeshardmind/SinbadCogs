# These stubs are possibly wrong.
# They were generated with monkeytype and are "good enough"
# After some minor corrections
from typing import Callable, List, Type, Union

from pyparsing import CaselessLiteral, Literal, Suppress, Word, _SingleCharLiteral

from .elements import (
    Dice,
    FudgeDice,
    Integer,
    IntegerList,
    Roll,
    String,
    WildDice,
    WildRoll,
)

def _trim_arity(func: Callable, maxargs: None = ...) -> Callable: ...
def dice_switch(
    amount: Integer, dicetype: Integer, kind: String = ...
) -> Union[FudgeDice, Dice, WildDice]: ...
def disable_pyparsing_arity_trimming() -> None: ...
def enable_pyparsing_packrat() -> None: ...
def patch_pyparsing(packrat: bool = ..., arity: bool = ...) -> None: ...
def single(
    iterable: Union[List[WildRoll], List[Roll], List[IntegerList]]
) -> Union[IntegerList, Roll, WildRoll]: ...
def wrap_string(
    cls: Union[Type[CaselessLiteral], Type[Literal], Type[Word]], *args, **kwargs
) -> Union[_SingleCharLiteral, Suppress, CaselessLiteral]: ...
