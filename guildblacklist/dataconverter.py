import json
import pathlib


class DataConverter:

    def __init__(self, config_instance):
        self.config = config_instance

    def load_json(self, path: pathlib.Path):
        with open(path, mode='r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                raise ValueError
            else:
                return data

    async def convert(self, path: str, converter: dict):
        _path = pathlib.Path(str)
        if not _path.exists:
            raise FileNotFoundError
            return

        try:
            v2_data = self.load_json(_path)
        except ValueError:
            raise
            return

        for k, v in converter.items():
            await self.config.set_attr(k, v(v2_data))