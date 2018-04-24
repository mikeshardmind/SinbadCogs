import resource
import subprocess
import sys
import pathlib
import shlex
import functools
import asyncio

from redbot.core.bot import RedContext


def setlimits(*, timeout: int=60, memlimit: int=50):
    resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
    mb_as_b = memlimit * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_MEMLOCK, (mb_as_b, mb_as_b))


async def run_jailed(
        *, expr: str,
        timeout: int=60,
        memlimit: int=60,
        ctx: RedContext):

    file_str = str(pathlib.Path(__file__).parent / 'jailed_calc.py')
    run_args = [sys.executable, file_str]
    run_args.extend(shlex.quote(expr).split())
    runstr = ' '.join(run_args)
    prexec = functools.partial(setlimits, timeout=timeout, memlimit=memlimit)
    p = await asyncio.create_subprocess_shell(
        runstr,
        preexec_fn=prexec,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    try:
        _outs, errs = await p.communicate()
    except Exception:
        p.kill()
        _outs, errs = await p.communicate()

    outs = _outs.decode()

    await ctx.send(
        ('input: \n'
         '```py\n{expr}\n```\noutput:\n'
         '```\n{outs}\n```').format(expr=expr, outs=outs)
    )
