from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

import apsw

"""
This should be moved into a pip installable lib at some point, but I'm being
lazy in the short term here.
"""


if TYPE_CHECKING:
    from typing_extensions import Protocol
else:
    Protocol = object


class ProvidesCursor(Protocol):
    def cursor(self) -> apsw.Cursor:
        ...


class ContextManagerMixin(ProvidesCursor):
    @contextmanager
    def with_cursor(self) -> Generator[apsw.Cursor, None, None]:
        c = self.cursor()
        try:
            yield c
        finally:
            c.close()

    @contextmanager
    def transaction(self) -> Generator[apsw.Cursor, None, None]:
        c = self.cursor()
        try:
            c.execute("BEGIN TRANSACTION")
            yield c
        except Exception:
            c.execute("ROLLBACK TRANSACTION")
            raise
        else:
            c.execute("COMMIT TRANSACTION")
        finally:
            c.close()


class Connection(apsw.Connection, ContextManagerMixin):
    pass


# TODO: asyncio friendly ThreadedConnection class
