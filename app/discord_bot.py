from __future__ import annotations

import logging

import discord

from .parser import missing_info_reply, parse_message
from .service import RequestService

log = logging.getLogger(__name__)


class DiscordRequestBot(discord.Client):
    def __init__(self, *, service: RequestService, guild_id: int | None, channel_ids: list[int], reply_mode: str = "reply"):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.service = service
        self.guild_id = guild_id
        self.channel_ids = set(channel_ids)
        self.reply_mode = reply_mode

    async def on_ready(self) -> None:
        log.info("Discord connected as %s", self.user)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.guild_id and (not message.guild or message.guild.id != self.guild_id):
            return
        if self.channel_ids and message.channel.id not in self.channel_ids:
            return

        requests = parse_message(message.content)
        if not requests:
            return

        incomplete = [r for r in requests if not r.is_complete]
        if incomplete:
            reply = missing_info_reply(incomplete)
            if reply:
                # This is a normal message reply visible to the sender/channel.
                # Discord cannot make a regular message reply visible only to one user;
                # use DM if strict privacy is required.
                try:
                    if self.reply_mode == "dm":
                        await message.author.send(reply)
                    else:
                        await message.reply(reply, mention_author=True, delete_after=120)
                except discord.Forbidden:
                    try:
                        await message.author.send(reply)
                    except discord.Forbidden:
                        log.warning("Cannot reply or DM user %s", message.author.id)

        for req in requests:
            await self.service.process(
                req,
                discord_message_id=str(message.id),
                discord_user_id=str(message.author.id),
                discord_channel_id=str(message.channel.id),
                original_message=message.content,
            )
