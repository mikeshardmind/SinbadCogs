import json
import pathlib


class DataConverter:

    def __init__(self, cog_instance, config_instance):
        self.cog = cog_instance
        self.config = config_instance

    def load_json(self, path: pathlib.Path):
        with open(path, mode='r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                raise ValueError
            else:
                return data

    async def convert(self, path: str):
        _path = pathlib.Path(str)
        if not _path.exists:
            raise FileNotFoundError
            return

        try:
            v2_data = self.load_json(_path)
        except ValueError:
            raise
            return

        # cog specific stuff here, generalize this with
        # a format spec of some sort later, this works for now
        # once format spec handling is ready, PR it as a util
        # for core red

        _ids = set(
            int(i) for i in v2_data.keys()
        )
        async with self.config.blacklist() as bl:
            bl.update(_ids)
