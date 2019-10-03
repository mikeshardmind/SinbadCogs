import importlib

from . import core, abc, converters, events, exceptions, massmanager, utils
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):

    # ordering important based on which may import another
    for mod in (abc, converters, exceptions, events, massmanager, utils):
        importlib.reload(mod)

    module = importlib.reload(core)
    bot.add_cog(module.RoleManagement(bot))
