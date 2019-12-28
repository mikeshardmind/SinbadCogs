import discordtextsanitizer as dts
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import pagify
from .restrictedenvironment import RestrictedEnv


class Templater(commands.Cog):
    """ meh """

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

        result = dts.sanitize_mass_mentions(result, run_preprocess=True)

        for page in pagify(result):
            await ctx.send(page)
