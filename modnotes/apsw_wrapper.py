#   Copyright 2017-present Michael Hall
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

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

