# The below file is
# A python implementation of
# cowsay <http://www.nog.net/~tony/warez/cowsay.shtml>
# Licensed under the GNU LGPL version 3.0
import textwrap
from typing import List


COW_BASE = r"""
         \   ^__^
          \  (oo)\_______
             (__)\       )\/\
                 ||----w |
                 ||     ||
    """


def cowsay(text, length=40) -> str:
    return build_bubble(text, length) + COW_BASE


def build_bubble(text: str, length=40) -> str:
    bubble = []

    lines = normalize_text(text, length)

    bordersize = len(lines[0])

    bubble.append("  " + "_" * bordersize)

    for index, line in enumerate(lines):
        border = get_border(lines, index)

        bubble.append("%s %s %s" % (border[0], line, border[1]))

    bubble.append("  " + "-" * bordersize)

    return "\n".join(bubble)


def normalize_text(text: str, length: int) -> List[str]:
    extra = ""
    attrib = "\n        \u2015"
    if attrib in text:
        text, extra = text.rsplit(attrib, 1)
        extra = attrib + extra
    lines = textwrap.wrap(text, length)
    if extra:
        lines += textwrap.wrap(extra, length)
    maxlen = max(len(ln) for ln in lines)
    return [line.ljust(maxlen) for line in lines]


def get_border(lines: List[str], index: int) -> List[str]:
    if len(lines) < 2:
        return ["<", ">"]

    if index == 0:
        return ["/", "\\"]

    if index == len(lines) - 1:
        return ["\\", "/"]

    return ["|", "|"]
