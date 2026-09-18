from __future__ import annotations

import logging
from typing import Awaitable, Callable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from .arr_client import Match

log = logging.getLogger(__name__)

ReviewHandler = Callable[[int, int | None], Awaitable[None]]


class TelegramReviewBot:
    def __init__(self, token: str, admin_chat_id: int | None):
        self.admin_chat_id = admin_chat_id
        self.app = Application.builder().token(token).build() if token else None
        self._handler: ReviewHandler | None = None
        if self.app:
            self.app.add_handler(CallbackQueryHandler(self._on_callback))

    def set_review_handler(self, handler: ReviewHandler) -> None:
        self._handler = handler

    async def start(self) -> None:
        if not self.app:
            return
        await self.app.initialize()
        await self.app.start()
        assert self.app.updater
        await self.app.updater.start_polling(drop_pending_updates=False)

    async def stop(self) -> None:
        if not self.app:
            return
        assert self.app.updater
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_review(self, request_id: int, summary: str, matches: list[Match]) -> None:
        if not self.app or self.admin_chat_id is None:
            log.warning("Telegram is not configured; review %s cannot be delivered", request_id)
            return
        rows = []
        for idx, match in enumerate(matches[:5]):
            rows.append([InlineKeyboardButton(f"{idx + 1}. {match.label}", callback_data=f"pick:{request_id}:{idx}")])
        rows.append([InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{request_id}")])
        await self.app.bot.send_message(
            chat_id=self.admin_chat_id,
            text=summary,
            reply_markup=InlineKeyboardMarkup(rows),
        )

    async def send_error(self, text: str) -> None:
        if self.app and self.admin_chat_id is not None:
            await self.app.bot.send_message(chat_id=self.admin_chat_id, text=text)

    async def _on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not query.data:
            return
        if self.admin_chat_id is not None and query.message and query.message.chat_id != self.admin_chat_id:
            await query.answer("Not authorized", show_alert=True)
            return
        await query.answer()
        if not self._handler:
            return
        parts = query.data.split(":")
        if parts[0] == "pick" and len(parts) == 3:
            await self._handler(int(parts[1]), int(parts[2]))
            await query.edit_message_reply_markup(reply_markup=None)
        elif parts[0] == "cancel" and len(parts) == 2:
            await self._handler(int(parts[1]), None)
            await query.edit_message_reply_markup(reply_markup=None)
