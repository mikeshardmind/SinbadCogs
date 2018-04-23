import asteval
import sys


def run_in_jail(expr):
    evaler = asteval.Interpreter()
    evaler.eval(expr, show_errors=False)


if __name__ == '__main__':
    run_in_jail(sys.argv[1:])
