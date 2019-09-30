import importlib
from . import core
from . import converters, events, abc, exceptions, massmanager, utils
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    for extra in (converters, abc, exceptions, utils, massmanager, events):
        importlib.reload(extra)
    core = importlib.reload(core)

    bot.add_cog(core.RoleManagement(bot))
