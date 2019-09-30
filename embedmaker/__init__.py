import importlib
from . import embedmaker, serialize, yaml_parse
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(serialize)
    importlib.reload(yaml_parse)
    embedmaker = embedmaker.reload(yaml_parse)
    bot.add_cog(embedmaker.EmbedMaker(bot))
