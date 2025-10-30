from __future__ import annotations
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from telebot import TeleBot
    from telebot.types import CallbackQuery, Message
    from tg_bot import TgBot

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from ..core.config import RefundConfig
from ..utils.constants import UIConstants, CallbackData
from tg_bot import CBT

logger = logging.getLogger("FPC.AutoRefund.TelegramUI")


class TelegramUIHandler:
    def __init__(self, bot: TeleBot, tg: TgBot, config: RefundConfig, uuid: str):
        self._bot = bot
        self._tg = tg
        self._config = config
        self._uuid = uuid
        self._awaiting_price: set[int] = set()
        self._awaiting_text: set[int] = set()

    def register_handlers(self) -> None:
        self._tg.cbq_handler(self._show_settings, lambda c: f"{CBT.PLUGIN_SETTINGS}:{self._uuid}" in c.data)
        self._tg.cbq_handler(self._toggle_setting, lambda c: CallbackData.SWITCH in c.data)
        self._tg.cbq_handler(self._request_price, lambda c: CallbackData.PRICE_CHANGE in c.data)
        self._tg.cbq_handler(self._request_text, lambda c: CallbackData.TEXT_CHANGE in c.data)
        
        self._tg.msg_handler(self._handle_price_input, func=lambda m: m.from_user.id in self._awaiting_price)
        self._tg.msg_handler(self._handle_text_input, func=lambda m: m.from_user.id in self._awaiting_text)

    def _show_settings(self, call: CallbackQuery) -> None:
        try:
            kb = InlineKeyboardMarkup()
            
            kb.add(
                InlineKeyboardButton(
                    f"Возврат до: {self._config.max_price}₽",
                    callback_data=CallbackData.PRICE_CHANGE
                )
            )
            
            preview_text = self._config.blacklist_message[:20] + "..."
            kb.add(
                InlineKeyboardButton(
                    f"Текст ЧС: {preview_text}",
                    callback_data=CallbackData.TEXT_CHANGE
                )
            )
            
            options = [
                ("Добавлять в ЧС", "block_user"),
                ("Уведомления", "refund_notification"),
                ("ЧС при удалении отзыва", "feedback_delete")
            ]
            
            for label, key in options:
                state = UIConstants.CHECK_MARK if getattr(self._config, key) else UIConstants.CROSS_MARK
                kb.add(
                    InlineKeyboardButton(
                        label,
                        callback_data=f"{CallbackData.SWITCH}:{key}"
                    ),
                    InlineKeyboardButton(
                        state,
                        callback_data=f"{CallbackData.SWITCH}:{key}"
                    )
                )
            
            kb.add(InlineKeyboardButton("⭐ Настройка звезд", callback_data="dummy"))
            
            for stars in range(1, 6):
                state = "🟢" if getattr(self._config, f"star_{stars}") else "🔴"
                kb.row(
                    InlineKeyboardButton(
                        "⭐" * stars,
                        callback_data=f"{CallbackData.SWITCH}:star_{stars}"
                    ),
                    InlineKeyboardButton(
                        state,
                        callback_data=f"{CallbackData.SWITCH}:star_{stars}"
                    )
                )
            
            kb.add(InlineKeyboardButton("◀️ Назад", callback_data=f"{CBT.EDIT_PLUGIN}:{self._uuid}:0"))
            
            text = (
                "⚙️ Настройки автовозврата\n\n"
                f"💰 Максимальная сумма: {self._config.max_price}₽\n"
                f"📛 ЧС активен: {UIConstants.CHECK_MARK if self._config.block_user else UIConstants.CROSS_MARK}\n"
                f"🔔 Уведомления: {UIConstants.CHECK_MARK if self._config.refund_notification else UIConstants.CROSS_MARK}"
            )
            
            self._bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.id,
                reply_markup=kb
            )
            self._bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Error showing settings: {e}")

    def _toggle_setting(self, call: CallbackQuery) -> None:
        try:
            setting = call.data.split(":")[1]
            
            if setting == "refund_notification":
                current = self._config.refund_notification
                self._config.update(
                    refund_notification=not current,
                    refund_notification_chat_id=call.message.chat.id
                )
            else:
                current = getattr(self._config, setting, None)
                if current is not None:
                    self._config.update(**{setting: not current})
            
            self._show_settings(call)
        except Exception as e:
            logger.error(f"Error toggling setting: {e}")

    def _request_price(self, call: CallbackQuery) -> None:
        try:
            self._awaiting_price.add(call.from_user.id)
            self._bot.send_message(
                call.message.chat.id,
                "💰 Введите максимальную сумму для автовозврата (в рублях):"
            )
            self._bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Error requesting price: {e}")

    def _handle_price_input(self, message: Message) -> None:
        try:
            self._awaiting_price.discard(message.from_user.id)
            
            try:
                new_price = float(message.text)
                if new_price < 0:
                    raise ValueError("Negative price")
            except ValueError:
                self._bot.reply_to(
                    message,
                    "❌ Ошибка: введите корректное число"
                )
                return
            
            self._config.update(max_price=new_price)
            
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("◀️ К настройкам", callback_data=f"{CBT.PLUGIN_SETTINGS}:{self._uuid}"))
            
            self._bot.reply_to(
                message,
                f"✅ Максимальная сумма обновлена: {new_price}₽",
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"Error handling price: {e}")

    def _request_text(self, call: CallbackQuery) -> None:
        try:
            self._awaiting_text.add(call.from_user.id)
            self._bot.send_message(
                call.message.chat.id,
                f"📛 Текущее сообщение:\n<code>{self._config.blacklist_message}</code>\n\n"
                "Введите новое сообщение для пользователей из ЧС:",
                parse_mode="HTML"
            )
            self._bot.answer_callback_query(call.id)
        except Exception as e:
            logger.error(f"Error requesting text: {e}")

    def _handle_text_input(self, message: Message) -> None:
        try:
            self._awaiting_text.discard(message.from_user.id)
            self._config.update(blacklist_message=message.text)
            
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("◀️ К настройкам", callback_data=f"{CBT.PLUGIN_SETTINGS}:{self._uuid}"))
            
            self._bot.reply_to(
                message,
                "✅ Сообщение обновлено",
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"Error handling text: {e}")