import os
import pathlib
import discord
import logging
from datetime import datetime, timedelta

from redbot.core import checks, Config, commands
from redbot.core import data_manager

TIMESTAMP_FORMAT = "%Y-%m-%d %X"  # YYYY-MM-DD HH:MM:SS


class Logging:
    def __init__(self, bot):
        self.bot = bot
        self.path = data_manager.cog_data_path(cog_instance=self)

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        channel = discord.utils.get(
            self.bot.get_all_channels(), id=payload.data["channel_id"]
        )
        if channel is None or not type(message.channel) == discord.TextChannel:
            return
        content = payload.data.get("content", "")
        author = channel.guild.get_member(payload.data.get("id", 0))
        if not author:
            return
        time = datetime.utcnow().strftime(TIMESTAMP_FORMAT)
        path = self.path / f"{channel.guild.id}" / f"{channel.id}.log"
        text = f"[{time}] Message # {payload.message_id} edited: ({author.id}) {author}: {message.clean_content}"
        self.log(text, path)

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if not payload.guild_id:
            return
        channel = discord.utils.get(self.bot.get_all_channels(), id=payload.channel_id)
        time = datetime.utcnow().strftime(TIMESTAMP_FORMAT)
        path = self.path / f"{payload.guild_id}" / f"{payload.channel_id}.log"
        text = f"[{time}] Message # {payload.message_id} deleted"
        self.log(text, path)

    async def on_message(self, message: discord.Message):
        if not type(message.channel) == discord.TextChannel:
            return
        channel = message.channel
        author = message.author
        time = message.created_at.strftime(TIMESTAMP_FORMAT)
        text = f"[{time}] ({author.id}) {author} {message.clean_content}"
        path = self.path / f"{channel.guild.id}" / f"{channel.id}.log"
        self.log(text, path)
        if message.attachments:
            try:
                p = await self.attach_handler(message)
            except:
                self.log("Attachment save failed", path)
            else:
                self.log(f"Attachment saved to {p}.", path)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        time = datetime.utcnow().strftime(TIMESTAMP_FORMAT)
        path = self.path / f"{before.guild.id}" / "events.log"

        entries = []
        if before.nick != after.nick:
            entries.append(
                "Member nickname: '@{0}' (id {0.id}) changed nickname "
                "from '{0.nick}' to '{1.nick}'".format(before, after)
            )
        if before.name != after.name:
            entries.append(
                "Member username: '@{0}' (id {0.id}) changed username "
                "from '{0.name}' to '{1.name}'".format(before, after)
            )
        if before.roles != after.roles:
            broles = set(before.roles)
            aroles = set(after.roles)
            added = aroles - broles
            removed = broles - aroles
            for r in added:
                entries.append(
                    f"Member role add: '{r}' role was added to {after} ({after.id})"
                )
            for r in removed:
                entries.append(
                    f"Member role remove: The '{r}' role was removed from {after} ({after.id})"
                )
        for e in entries:
            text = f"[{time}] {e}"
            self.log(text, path)

    async def on_member_join(self, member):
        time = datetime.utcnow().strftime(TIMESTAMP_FORMAT)
        text = f"[{time}] Member join: {member} ({member.id})"
        path = self.path / f"{before.guild.id}" / "events.log"
        self.log(text, path)

    async def on_member_remove(self, member):
        time = datetime.utcnow().strftime(TIMESTAMP_FORMAT)
        text = f"[{time}] Member leave: {member} ({member.id})"
        path = self.path / f"{before.guild.id}" / "events.log"
        self.log(text, path)

    async def attach_handler(self, message: discord.Message):
        a = message.attachments[0]
        channel = message.channel
        author = message.author
        ts = message.created_at.strftime(TIMESTAMP_FORMAT)
        path = self.path / f"{channel.guild.id}" / f"{channel.id}" / "attachments"
        path.mkdir(exist_ok=True, parents=True)
        path = path / f"{ts}-{author.id}-{a.filename}"
        with path.open(mode="wb") as f:
            await s.save(f)
        return path

    def log(self, message: str, path: pathlib.Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        message = message.replace("\n", "\\n")
        with path.open(mode="a", encoding="utf-8", errors="backslashreplace") as f:
            f.write(message + "\n")
