from redbot.cogs.mod import mod


def attr_killer(*names):
    def actual_killer(cls):
        cls_dict = dict(cls.__dict__)
        for name in names:
            cls_dict.pop(name, None)
        bases = []
        for base in cls.__bases__:
            if base not in (object, type):
                bases.append(actual_killer(base))
            else:
                bases.append(base)
        cls = type(cls)(cls.__name__, tuple(bases), cls_dict)
        return cls

    return actual_killer


@attr_killer("on_member_update", "names")
class Mod(mod.Mod):
    async def get_names_and_nicks(self, user):
        """
        Dummy func for userinfo
        """
        return [], []
