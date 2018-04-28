import asyncio
from redbot.core import RedContext
from .serialize import deserialize_embed, template
# from dateutil.parser import parser
from redbot.core.utils.chat_formatting import box


# TODO: decide if this should be used
class Interactive:

    def __init__(self, ctx: RedContext, bot):
        self.ctx = ctx
        self.bot = bot
        self.embed_dict = {}
        self._preview = None
        self._prompts = None

    @property
    def embed(self):
        if self.embed_dict:
            return deserialize_embed(self.embed_dict)
        else:
            return None

    def nested_set(self, *ids, value):
        partial = self.data
        for i in ids[:-1]:
            if i not in partial:
                partial[i] = {}
            partial = partial[i]
        partial[ids[-1]] = value

    async def menu(self):
        if self._prompt:
            await self._prompt.delete()

        menu = {}
        for k, v in template.items():
            for thing in v.keys():
                menu['Set {}'.format(v)] = {
                    'ids': (k, v),
                    'func': getattr(self, 'set_' + thing)
                }
        menu_list = list(sorted(menu.keys()))

        while True:
            output = (
                "What would you like to do?")
            for i, k in enumerate(menu_list, 1):
                output += "\n{num}. {action}"(num=i, action=k)
            output += (
                "\n\nYou can select any of the above by number, use "
                "`s` to save the current embed, "
                "or use `q` to quit without saving")

            self._prompt = await self.ctx.send(box(output), embed=self.embed)

            def pred(m):
                return (
                    m.channel == self.ctx.channel
                    and m.author == self.ctx.author
                )
            try:
                message = await self.bot.wait_for(
                    'message', check=pred, timeout=60
                )
            except asyncio.TimeoutError:
                await self._prompt.edit(
                    content='try again later then...', embed=None)
                return None

            if message.content.strip().lower() == 'q':
                return None
            elif message.content.strip().lower() == 's':
                return self.embed_dict
            else:
                try:
                    message = int(message.content.strip())
                    if message < 1:
                        raise ValueError('K')
                    opt = menu_list[message - 1]
                except (ValueError, IndexError):
                    await self.ctx.edit(
                        content='Invalid choice, try again later', embed=None)
                    return None
                else:
                    await menu[opt]()
