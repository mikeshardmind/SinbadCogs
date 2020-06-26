import datetime

from .mixins import Hashable

class Object(Hashable):
    id: int
    def __init__(self, id: int) -> None: ...
    @property
    def created_at(self) -> datetime.datetime: ...
