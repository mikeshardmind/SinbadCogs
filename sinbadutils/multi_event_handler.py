# MIT Licensed: See https://github.com/mikeshardmind/SinbadCogs/blob/v3/LICENSE
# or bottom of file
import asyncio
from typing import Dict, Callable
from discord import Client

Check = Callable[..., bool]
EventDict = Dict[str, Check]


async def wait_for_any(*, bot: Client, event_dict: EventDict, timeout: int = None) -> tuple:
    """
    Takes
    bot
    a dict of event -> checks,
    optional timout

    Returns the first to match

    if none match before a prior timeout, raises asyncio.TimeoutError
    """
    def _check(*args):
        return True
    futures = []
    for event, check in event_dict.items():
        future = bot.loop.create_future()
        if check is None:
            check = _check

        ev = event.lower()
        try:
            listeners = bot._listeners[ev]
        except KeyError:
            listeners = []
            bot._listeners[ev] = listeners

        bot.listeners.append((future, check))
        futures.append(future)

    completed, unfinished = await asyncio.wait(
        *futures, timeout=timeout, loop=bot.loop, return_when=asyncio.FIRST_COMPLETED
    )
    [t.cancel() for t in unfinished]
    try:
        result = next(filter(None, completed)).result()
    except StopIteration:
        raise asyncio.TimeoutError()
    else:
        return result

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
