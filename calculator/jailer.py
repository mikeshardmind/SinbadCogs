import resource
import subprocess
import sys
import pathlib
import shlex
import functools
import asyncio


def setlimits(*, timeout: int=60, memlimit: int=50):
    resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
    mb_as_b = memlimit * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (mb_as_b, mb_as_b))


def run_jailed(
        expr: str, *,
        timeout: int=60,
        memlimit: int=60,
        callback: callable=None,
        context=None):

    file_str = str(pathlib.Path(__file__).parent / 'jailed_calc.py')
    run_args = [sys.executable, file_str]
    run_args.extend(shlex.quote(expr).split())
    prexec = functools.partial(setlimits, timeout=timeout, memlimit=memlimit)
    p = subprocess.Popen(
        run_args,
        preexec_fn=prexec,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    p.wait()

    if p.returncode == 0:
        ret = p.stdout.getvalue()
    else:
        ret = None

    if callback is None:
        return ret
    else:
        asyncio.get_event_loop().create_task(
            callback, context, ret
        )
