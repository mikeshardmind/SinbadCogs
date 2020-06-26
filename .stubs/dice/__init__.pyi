# These stubs are possibly wrong.
# They were generated with monkeytype and are "good enough"
# After some minor corrections
from typing import Any, Union

from .elements import IntegerList, Roll, WildRoll

def _roll(
    string: str,
    single: bool = ...,
    raw: bool = ...,
    return_kwargs: bool = ...,
    **kwargs,
) -> Union[WildRoll, IntegerList, Roll]: ...
def parse_expression(string: str) -> Any: ...
def roll(string: str, **kwargs) -> Union[WildRoll, IntegerList, Roll]: ...
def roll_max(string: str, **kwargs) -> Union[WildRoll, IntegerList, Roll]: ...
def roll_min(string: str, **kwargs) -> Union[WildRoll, IntegerList, Roll]: ...
