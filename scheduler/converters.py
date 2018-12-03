import argparse
from redbot.core import commands


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise commands.BadArgument()
