from typing import BinaryIO, Optional, Union

class File:
    fp: Union[str, BinaryIO]
    filename: Optional[str]
    def __init__(
        self,
        fp: Union[str, BinaryIO],
        filename: Optional[str] = ...,
        *,
        spoiler: bool = ...,
    ) -> None: ...
    def reset(self, *, seek: bool = ...) -> None: ...
    def close(self) -> None: ...
