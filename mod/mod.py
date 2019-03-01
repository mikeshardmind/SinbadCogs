from redbot.cogs.mod import mod


def attr_killer(*names):

    def actual_killer(cls):
        cls_dict = dict(cls.__dict__)
        for name in names:
            cls_dict.pop(name, None)
        cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)
        return cls

    return actual_killer

@attr_killer("on_member_update")
class Mod(mod.Mod):

    async def get_names_and_nicks(self, user):
        """
        Dummy func for userinfo
        """
        return [], []
