from redbot.cogs.mod import mod


class Mod(mod.Mod):
    """
    I *wanted* to make a new class from the existing one, but compositing in future of mod
    makes that a tad bit more work than I want for this.
    """

    async def get_names_and_nicks(self, *args, **kwargs):
        # dummy func so userinfo doesnt break
        return [], []

    async def on_member_update(self, *args, **kwargs):
        # kill saving member name changes, also popped during setup.
        pass

    @property
    def names(self):  # kill now useless command
        return None


Mod.__doc__ = mod.Mod.__doc__  # preserve help
