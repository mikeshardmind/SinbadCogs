import asyncio
import concurrent.futures
from io import BytesIO
from functools import partial
import pickle  # nosec: B403

from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import pagify
from .restrictedenvironment import RestrictedEnv


class SkipPickler(pickle.Pickler):
    def dump(self, obj):
        try:
            return super().dump(obj)
        except Exception:
            return None


def safe_ctx(ctx):
    s = BytesIO()
    SkipPickler(s).dump(ctx)
    s.seek(0)
    return pickle.load(s)  # nosec: B301


def handle_template(template, ctx) -> str:
    e = RestrictedEnv(trim_blocks=True, lstrip_blocks=True)
    e.globals = e.make_globals({"ctx": ctx})

    try:
        t = e.from_string(template)
        result = t.render()
    except Exception as exc:
        result = f"{type(exc)}:\n{exc}"

    return result


class Templater(commands.Cog):
    """ meh """

    def __init__(self):
        super().__init__()
        self.pool = concurrent.futures.ProcessPoolExecutor()

    def cog_unload(self):
        self.pool.shutdown()

    @checks.is_owner()
    @commands.command()
    async def tdebug(self, ctx: commands.Context, *, template: str):
        """ This is probably a terrible idea """
        e = RestrictedEnv(trim_blocks=True, lstrip_blocks=True)
        e.globals = e.make_globals({"ctx": ctx})

        try:
            t = e.from_string(template)
            result = t.render()
        except Exception as exc:
            result = f"{type(exc)}:\n{exc}"

        for page in pagify(result):
            await ctx.send(page)

    @checks.is_owner()
    @commands.command()
    async def tpdebug(self, ctx, *, template: str):

        with self.pool as p:
            pickled = safe_ctx(ctx)
            func = partial(handle_template, template, pickled)
            result = await asyncio.get_event_loop().run_in_executor(p, func)

        for page in pagify(result):
            await ctx.send(page)
