import discordtextsanitizer as dts
from discord.utils import escape_mentions
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils import menus

from .restrictedenvironment import RestrictedEnv


class Templater(commands.Cog):
    """ meh """

    @checks.is_owner()
    @commands.command()
    async def template(self, ctx: commands.Context, *, template: str):
        """
        This is probably a terrible idea

        context is exposed as `ctx`
        """
        e = RestrictedEnv(trim_blocks=True, lstrip_blocks=True)
        e.globals = e.make_globals({"ctx": ctx})

        try:
            t = e.from_string(template)
            result = t.render()
        except Exception as exc:
            result = f"{type(exc)}:\n{exc}"

        result = dts.preprocess_text(result)
        result = escape_mentions(result)
        pages = list(pagify(result))
        if pages:
            await menus.menu(ctx, pages, menus.DEFAULT_CONTROLS)
