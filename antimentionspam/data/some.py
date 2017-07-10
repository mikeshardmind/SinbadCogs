async def get_msg(self, message_id: str, server=None):
    if server is not None:
        for channel in server.channels:
            try:
                msg = await self.bot.get_message(channel, message_id)
                if msg:
                    return msg
            except Exception:
                pass
        return None

    for server in self.bot.servers:
        for channel in server.channels:
            try:
                msg = await self.bot.get_message(channel,  message_id)
                if msg:
                    return msg
            except Exception:
                pass
