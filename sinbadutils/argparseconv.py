# MIT Licensed: See https://github.com/mikeshardmind/SinbadCogs/blob/v3/LICENSE
# or bottom of file
import argparse
import shlex
from typing import Dict

from discord.utils import maybe_coroutine
from redbot.core import commands
from redbot.core.commands import Context  # *sigh* ignore this, mypy prefers it


# This might work, but it's just an idea I had and hasn't been finished or tested yet.
class ArgParsedConverter(commands.Converter):
    """
    Okay, so this can still use improvement, and isn't even ready for use.
    and isn't going to be well documented until then.
    Maybe not even then if I just kill it by doing the other thing.
    """

    def __init__(
        self, *, parser: argparse.ArgumentParser, transformers: dict = None
    ) -> None:
        self.parser = parser
        self.transformers = transformers or {}

    def __call__(self):
        """
        This is an intentional abuse of the data model
        to avoid undesireable behavior with discord.py
        until I'm ready to just ditch it's commands extension entirely.
        for this and other reasons.
        """
        return self

    @classmethod
    def from_info(cls, data: dict, transformers: dict = None):
        """
        TODO: add stuff to generate this without manually creating a parser
        """
        pass

    async def convert(self, ctx: Context, argument: str) -> dict:

        namespace = self.parser.parse_args(shlex.split(argument))
        ret = vars(namespace)

        for argname, transformer in self.transformers.items():
            if hasattr(ret[argname], "__iter__") and not transformer.get(
                "expect_multi", False
            ):
                temp_data = []
                for val in ret[argname]:
                    temp_data.append(await maybe_coroutine(transformer["func"], val))
                ret[argname] = type(ret[argname])(temp_data)
            else:
                ret[argname] = await maybe_coroutine(transformer["func"], ret[argname])
        return ret


# License info is here at the bottom because
# who wants to open up source code and see the license first?
#
# MIT License
#
# Copyright (c) 2017-2018 Michael Hall
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
