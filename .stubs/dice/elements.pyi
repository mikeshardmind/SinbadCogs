# These stubs are possibly wrong.
# They were generated with monkeytype and are "good enough"
# After some minor corrections
from typing import Any, List, Optional, SupportsInt, Type, Union

Integer = int
IntegerList = List[Integer]
String = str

class Array:
    def function(self, *args) -> IntegerList: ...

class Dice:
    def __init__(
        self, amount: Integer, max_value: Integer, min_value: int = ...
    ) -> None: ...

class Element:
    def evaluate(self, **kwargs) -> Integer: ...
    def evaluate_cached(
        self, **kwargs
    ) -> Union[IntegerList, Integer, Roll, WildRoll]: ...
    @staticmethod
    def evaluate_object(
        obj: Union[Integer, Dice, int],
        cls: Optional[Type[Integer]] = ...,
        cache: bool = ...,
        **kwargs,
    ) -> Union[Integer, Roll]: ...
    @classmethod
    def parse(
        cls, string: str, location: int, tokens: Any
    ) -> Union[Array, Integer, String]: ...
    def set_parse_attributes(
        self, string: str, location: int, tokens: Any
    ) -> Element: ...

class FudgeDice:
    def __init__(self, amount: Integer, range: Integer) -> None: ...

class Operator:
    def __init__(self, *operands) -> None: ...
    def evaluate(self, **kwargs) -> IntegerList: ...
    def preprocess_operands(
        self, *operands, **kwargs
    ) -> List[Union[Roll, Integer]]: ...

class RandomElement:
    def __init__(
        self, amount: Integer, min_value: int, max_value: Integer, **kwargs
    ) -> None: ...
    def evaluate(self, **kwargs) -> Roll: ...
    @classmethod
    def parse(
        cls, string: str, location: int, tokens: Any
    ) -> Union[FudgeDice, Dice, WildDice]: ...
    @classmethod
    def register_dice(
        cls, new_cls: Union[Type[WildDice], Type[FudgeDice], Type[Dice]]
    ) -> Union[Type[WildDice], Type[FudgeDice], Type[Dice]]: ...

class Roll(SupportsInt):
    def __init__(
        self, element: Union[FudgeDice, Dice, WildDice], rolled: None = ..., **kwargs
    ) -> None: ...
    def do_roll(
        self, amount: None = ..., min_value: None = ..., max_value: None = ..., **kwargs
    ) -> List[int]: ...
    @classmethod
    def roll(
        cls, orig_amount: Integer, min_value: int, max_value: Integer, **kwargs
    ) -> List[int]: ...
    @classmethod
    def roll_single(cls, min_value: int, max_value: Integer, **kwargs) -> int: ...
    def __int__(self) -> int: ...

class WildDice:
    def evaluate(self, **kwargs) -> WildRoll: ...

class WildRoll(SupportsInt):
    @classmethod
    def roll(
        cls, amount: Integer, min_value: int, max_value: Integer, **kwargs
    ) -> List[int]: ...
    def __int__(self) -> int: ...
